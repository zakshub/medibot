"""Atomic artifact storage restricted to a configured project directory."""

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def safe_artifact_key(key: str) -> PurePosixPath:
    normalized = PurePosixPath(key)
    if normalized.is_absolute() or not normalized.parts:
        raise ValueError("artifact key must be relative")
    if any(
        part in {"", ".", ".."} or not _SAFE_SEGMENT.fullmatch(part) for part in normalized.parts
    ):
        raise ValueError("artifact key contains an unsafe path segment")
    return normalized


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    key: str
    path: Path
    content_type: str
    sha256: str
    size_bytes: int


class LocalArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_key(key: str) -> PurePosixPath:
        return safe_artifact_key(key)

    def write_bytes(self, key: str, payload: bytes, *, content_type: str) -> StoredArtifact:
        safe_key = self._safe_key(key)
        destination = self.root.joinpath(*safe_key.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(destination)
        digest = sha256(payload).hexdigest()
        return StoredArtifact(key, destination, content_type, digest, len(payload))

    def write_text(self, key: str, value: str, *, content_type: str) -> StoredArtifact:
        return self.write_bytes(key, value.encode("utf-8"), content_type=content_type)
