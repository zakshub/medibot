"""Hash-verified encrypted mirroring to an S3-compatible object store."""

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Protocol
from urllib.parse import urlparse

from medibot.artifact_store import StoredArtifact, safe_artifact_key

_BUCKET = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


class S3ObjectClient(Protocol):
    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def head_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def generate_presigned_url(
        self,
        client_method: str,
        *,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class CloudArtifact:
    key: str
    uri: str
    content_type: str
    sha256: str
    size_bytes: int
    encryption: str


class S3ArtifactStore:
    def __init__(
        self,
        client: S3ObjectClient,
        *,
        bucket: str,
        prefix: str = "",
        kms_key_id: str | None = None,
        require_https_urls: bool = True,
    ) -> None:
        if not _BUCKET.fullmatch(bucket) or ".." in bucket:
            raise ValueError("S3 bucket name is invalid")
        if kms_key_id is not None and not kms_key_id.strip():
            raise ValueError("S3 KMS key ID cannot be blank")
        self.client = client
        self.bucket = bucket
        self.prefix = ""
        if prefix:
            self.prefix = safe_artifact_key(prefix.strip("/")).as_posix()
        self.kms_key_id = kms_key_id
        self.require_https_urls = require_https_urls

    def _object_key(self, key: str) -> str:
        safe = safe_artifact_key(key).as_posix()
        return f"{self.prefix}/{safe}" if self.prefix else safe

    def upload_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str,
    ) -> CloudArtifact:
        if not payload:
            raise ValueError("cloud artifact cannot be empty")
        if not content_type.strip() or len(content_type) > 200:
            raise ValueError("artifact content type is invalid")
        object_key = self._object_key(key)
        digest = sha256(payload).hexdigest()
        encryption = "aws:kms" if self.kms_key_id else "AES256"
        request: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": object_key,
            "Body": payload,
            "ContentType": content_type,
            "Metadata": {"sha256": digest},
            "ServerSideEncryption": encryption,
        }
        if self.kms_key_id:
            request["SSEKMSKeyId"] = self.kms_key_id
        self.client.put_object(**request)
        self._verify_remote(
            object_key,
            digest=digest,
            size_bytes=len(payload),
            encryption=encryption,
        )
        return CloudArtifact(
            object_key,
            f"s3://{self.bucket}/{object_key}",
            content_type,
            digest,
            len(payload),
            encryption,
        )

    def upload(self, artifact: StoredArtifact) -> CloudArtifact:
        payload = artifact.path.read_bytes()
        digest = sha256(payload).hexdigest()
        if digest != artifact.sha256 or len(payload) != artifact.size_bytes:
            raise ValueError("local artifact changed before cloud upload")
        return self.upload_bytes(
            artifact.key,
            payload,
            content_type=artifact.content_type,
        )

    def _verify_remote(
        self,
        key: str,
        *,
        digest: str,
        size_bytes: int,
        encryption: str,
    ) -> None:
        head = self.client.head_object(Bucket=self.bucket, Key=key)
        metadata = {
            str(name).casefold(): str(value) for name, value in head.get("Metadata", {}).items()
        }
        if int(head.get("ContentLength", -1)) != size_bytes:
            raise RuntimeError("cloud artifact size verification failed")
        if metadata.get("sha256") != digest:
            raise RuntimeError("cloud artifact hash metadata verification failed")
        if head.get("ServerSideEncryption") != encryption:
            raise RuntimeError("cloud artifact encryption verification failed")
        if encryption == "aws:kms" and not head.get("SSEKMSKeyId"):
            raise RuntimeError("cloud artifact KMS verification failed")

    def download_bytes(self, key: str, *, expected_sha256: str) -> bytes:
        if len(expected_sha256) != 64:
            raise ValueError("expected cloud artifact hash must be SHA-256")
        object_key = self._object_key(key)
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        body = response.get("Body")
        if body is None or not hasattr(body, "read"):
            raise RuntimeError("cloud artifact response body is invalid")
        payload = body.read()
        if not isinstance(payload, bytes) or sha256(payload).hexdigest() != expected_sha256:
            raise RuntimeError("downloaded cloud artifact hash verification failed")
        return payload

    def presigned_download_url(self, key: str, *, expires_seconds: int = 900) -> str:
        if not 60 <= expires_seconds <= 3_600:
            raise ValueError("presigned URL expiry must be between 60 and 3600 seconds")
        object_key = self._object_key(key)
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expires_seconds,
        )
        parsed = urlparse(url)
        if not parsed.hostname or (self.require_https_urls and parsed.scheme != "https"):
            raise RuntimeError("object store returned an unsafe presigned URL")
        return url


def create_boto3_s3_client(
    *,
    region_name: str | None = None,
    endpoint_url: str | None = None,
) -> S3ObjectClient:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("install medibot[cloud] to use S3 storage") from exc
    return boto3.client("s3", region_name=region_name, endpoint_url=endpoint_url)
