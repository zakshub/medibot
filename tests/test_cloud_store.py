from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from medibot.artifact_store import LocalArtifactStore
from medibot.cloud_store import S3ArtifactStore


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}
        self.last_put: dict[str, Any] | None = None
        self.url = "https://objects.example.test/signed"
        self.corrupt_head_hash = False

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self.last_put = kwargs
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = dict(kwargs)
        return {"ETag": "synthetic"}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        value = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        metadata = value["Metadata"]
        if self.corrupt_head_hash:
            metadata = {"sha256": "0" * 64}
        return {
            "ContentLength": len(value["Body"]),
            "Metadata": metadata,
            "ServerSideEncryption": value["ServerSideEncryption"],
            "SSEKMSKeyId": value.get("SSEKMSKeyId"),
        }

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        value = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {"Body": BytesIO(value["Body"])}

    def generate_presigned_url(
        self,
        client_method: str,
        *,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        assert client_method == "get_object"
        assert Params["Bucket"] == "medical-video-artifacts"
        assert ExpiresIn >= 60
        return self.url


def test_uploads_hash_verified_encrypted_artifact(tmp_path: Path) -> None:
    local = LocalArtifactStore(tmp_path / "local")
    artifact = local.write_bytes(
        "previews/video-1/preview.mp4",
        b"synthetic-video-payload",
        content_type="video/mp4",
    )
    client = FakeS3Client()
    cloud = S3ArtifactStore(
        client,
        bucket="medical-video-artifacts",
        prefix="production/mediloop",
    )

    result = cloud.upload(artifact)

    assert result.key == "production/mediloop/previews/video-1/preview.mp4"
    assert result.uri == (
        "s3://medical-video-artifacts/production/mediloop/previews/video-1/preview.mp4"
    )
    assert result.sha256 == artifact.sha256
    assert result.encryption == "AES256"
    assert client.last_put is not None
    assert client.last_put["ServerSideEncryption"] == "AES256"
    assert client.last_put["Metadata"] == {"sha256": artifact.sha256}


def test_kms_upload_download_and_presigned_url() -> None:
    client = FakeS3Client()
    cloud = S3ArtifactStore(
        client,
        bucket="medical-video-artifacts",
        kms_key_id="alias/mediloop-artifacts",
    )
    payload = b"reviewed-cloud-artifact"

    result = cloud.upload_bytes("approved/video.mp4", payload, content_type="video/mp4")
    downloaded = cloud.download_bytes(
        "approved/video.mp4",
        expected_sha256=sha256(payload).hexdigest(),
    )

    assert result.encryption == "aws:kms"
    assert client.last_put is not None
    assert client.last_put["SSEKMSKeyId"] == "alias/mediloop-artifacts"
    assert downloaded == payload
    assert cloud.presigned_download_url("approved/video.mp4") == client.url


def test_rejects_unsafe_keys_buckets_urls_and_expiry() -> None:
    client = FakeS3Client()
    with pytest.raises(ValueError, match="bucket"):
        S3ArtifactStore(client, bucket="Bad_Bucket")
    with pytest.raises(ValueError, match="KMS"):
        S3ArtifactStore(client, bucket="medical-video-artifacts", kms_key_id=" ")
    cloud = S3ArtifactStore(client, bucket="medical-video-artifacts")
    with pytest.raises(ValueError, match="unsafe path"):
        cloud.upload_bytes("../escape.mp4", b"payload", content_type="video/mp4")
    with pytest.raises(ValueError, match="expiry"):
        cloud.presigned_download_url("safe.mp4", expires_seconds=59)
    client.url = "http://objects.example.test/insecure"
    with pytest.raises(RuntimeError, match="unsafe"):
        cloud.presigned_download_url("safe.mp4")


def test_detects_remote_and_local_tampering(tmp_path: Path) -> None:
    client = FakeS3Client()
    cloud = S3ArtifactStore(client, bucket="medical-video-artifacts")
    local = LocalArtifactStore(tmp_path / "local")
    artifact = local.write_bytes("safe/video.mp4", b"original", content_type="video/mp4")
    artifact.path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        cloud.upload(artifact)

    payload = b"remote"
    client.corrupt_head_hash = True
    with pytest.raises(RuntimeError, match="hash"):
        cloud.upload_bytes("safe/remote.mp4", payload, content_type="video/mp4")
