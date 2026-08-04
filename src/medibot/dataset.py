"""Safe JSON manifest ingestion for an operator-supplied video dataset."""

import json
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from medibot.video_system import DomainProfile, VideoCandidate

_ALLOWED_VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".mkv", ".webm"})
_MAX_MANIFEST_BYTES = 5 * 1024 * 1024


class DomainManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    allowed_topics: list[str] = Field(min_length=1, max_length=500)
    allowed_keywords: list[str] = Field(min_length=1, max_length=2_000)
    blocked_keywords: list[str] = Field(default_factory=list, max_length=2_000)

    @field_validator("allowed_topics", "allowed_keywords", "blocked_keywords")
    @classmethod
    def normalize_terms(cls, values: list[str]) -> list[str]:
        normalized = sorted({item.strip().casefold() for item in values if item.strip()})
        if not normalized and values:
            raise ValueError("terms cannot be blank")
        return normalized


class VideoManifestItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    topic: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    script: str = Field(min_length=1, max_length=50_000)
    source_path: str | None = Field(default=None, max_length=1_000)
    duration_seconds: float | None = Field(default=None, gt=0, le=7_200)
    language: str = Field(default="en", pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    style_tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("style_tags")
    @classmethod
    def normalize_style_tags(cls, values: list[str]) -> list[str]:
        return sorted({item.strip().casefold() for item in values if item.strip()})


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1, le=1)
    domain: DomainManifest
    videos: list[VideoManifestItem] = Field(min_length=1, max_length=1_000)

    @model_validator(mode="after")
    def unique_ids(self) -> "DatasetManifest":
        ids = [item.candidate_id for item in self.videos]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique")
        return self


class DatasetManifestImporter:
    def __init__(self, dataset_root: Path) -> None:
        self.dataset_root = dataset_root.resolve()

    @staticmethod
    def load(manifest_path: Path) -> DatasetManifest:
        if manifest_path.stat().st_size > _MAX_MANIFEST_BYTES:
            raise ValueError("dataset manifest is too large")
        with manifest_path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
        return DatasetManifest.model_validate(raw)

    def _resolve_source(self, relative_path: str) -> Path:
        candidate = (self.dataset_root / relative_path).resolve()
        try:
            candidate.relative_to(self.dataset_root)
        except ValueError as exc:
            raise ValueError("video source must remain inside the dataset root") from exc
        if candidate.suffix.casefold() not in _ALLOWED_VIDEO_SUFFIXES:
            raise ValueError(f"unsupported video file type: {candidate.suffix}")
        if not candidate.is_file():
            raise ValueError(f"video source does not exist: {relative_path}")
        return candidate

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def convert(
        self, manifest: DatasetManifest
    ) -> tuple[DomainProfile, list[VideoCandidate]]:
        profile = DomainProfile(
            name=manifest.domain.name,
            allowed_topics=frozenset(manifest.domain.allowed_topics),
            allowed_keywords=frozenset(manifest.domain.allowed_keywords),
            blocked_keywords=frozenset(manifest.domain.blocked_keywords),
        )
        candidates = []
        for item in manifest.videos:
            source_path = None
            asset_hash = None
            if item.source_path is not None:
                source = self._resolve_source(item.source_path)
                source_path = str(source.relative_to(self.dataset_root))
                asset_hash = self._file_hash(source)
            candidates.append(
                VideoCandidate(
                    candidate_id=item.candidate_id,
                    topic=item.topic,
                    title=item.title,
                    script=item.script,
                    source_path=source_path,
                    duration_seconds=item.duration_seconds,
                    language=item.language,
                    style_tags=tuple(item.style_tags),
                    asset_sha256=asset_hash,
                )
            )
        return profile, candidates

