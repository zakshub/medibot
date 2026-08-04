"""Persistent idempotency and retry state for platform publication jobs."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from medibot.platforms import (
    Platform,
    PlatformApiError,
    PlatformPending,
    PublicationResult,
    PublishCommand,
)


@dataclass(frozen=True, slots=True)
class PublicationJob:
    job_key: str
    candidate_id: str
    platform: Platform
    artifact_sha256: str
    status: str
    attempts: int
    remote_id: str | None
    next_attempt_at: datetime | None
    last_error_code: str | None


@dataclass(frozen=True, slots=True)
class PublicationClaim:
    job: PublicationJob
    acquired: bool


class PublisherCall(Protocol):
    def __call__(self, command: PublishCommand) -> PublicationResult: ...


class PublicationStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS publication_jobs (
                    job_key TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(
                        status IN ('in_progress', 'retryable', 'published', 'failed')
                    ),
                    attempts INTEGER NOT NULL CHECK(attempts >= 0),
                    remote_id TEXT,
                    next_attempt_at TEXT,
                    last_error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(candidate_id, platform, artifact_sha256)
                )
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> PublicationJob:
        return PublicationJob(
            row["job_key"],
            row["candidate_id"],
            Platform(row["platform"]),
            row["artifact_sha256"],
            row["status"],
            row["attempts"],
            row["remote_id"],
            datetime.fromisoformat(row["next_attempt_at"]) if row["next_attempt_at"] else None,
            row["last_error_code"],
        )

    def claim(
        self,
        *,
        job_key: str,
        candidate_id: str,
        platform: Platform,
        artifact_sha256: str,
        now: datetime,
    ) -> PublicationClaim:
        if not job_key.strip() or not candidate_id.strip() or len(artifact_sha256) != 64:
            raise ValueError("job identity is invalid")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    """
                    SELECT * FROM publication_jobs
                    WHERE candidate_id = ? AND platform = ? AND artifact_sha256 = ?
                    """,
                    (candidate_id, platform.value, artifact_sha256),
                ).fetchone()
                acquired = False
                if row is None:
                    connection.execute(
                        """
                        INSERT INTO publication_jobs(
                            job_key, candidate_id, platform, artifact_sha256, status,
                            attempts, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, 'in_progress', 1, ?, ?)
                        """,
                        (
                            job_key,
                            candidate_id,
                            platform.value,
                            artifact_sha256,
                            now.isoformat(),
                            now.isoformat(),
                        ),
                    )
                    acquired = True
                elif row["status"] == "retryable" and (
                    row["next_attempt_at"] is None
                    or datetime.fromisoformat(row["next_attempt_at"]) <= now
                ):
                    connection.execute(
                        """
                        UPDATE publication_jobs
                        SET status='in_progress', attempts=attempts+1,
                            next_attempt_at=NULL, updated_at=?
                        WHERE job_key=?
                        """,
                        (now.isoformat(), row["job_key"]),
                    )
                    acquired = True
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            current = connection.execute(
                """
                SELECT * FROM publication_jobs
                WHERE candidate_id = ? AND platform = ? AND artifact_sha256 = ?
                """,
                (candidate_id, platform.value, artifact_sha256),
            ).fetchone()
        return PublicationClaim(self._from_row(current), acquired)

    def _transition(
        self,
        job_key: str,
        *,
        status: str,
        now: datetime,
        remote_id: str | None = None,
        next_attempt_at: datetime | None = None,
        error_code: str | None = None,
    ) -> PublicationJob:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE publication_jobs
                SET status=?, remote_id=?, next_attempt_at=?, last_error_code=?, updated_at=?
                WHERE job_key=? AND status='in_progress'
                """,
                (
                    status,
                    remote_id,
                    next_attempt_at.isoformat() if next_attempt_at else None,
                    error_code,
                    now.isoformat(),
                    job_key,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("publication job is not in progress")
            row = connection.execute(
                "SELECT * FROM publication_jobs WHERE job_key=?", (job_key,)
            ).fetchone()
        return self._from_row(row)

    def complete(
        self, job_key: str, *, remote_id: str, now: datetime
    ) -> PublicationJob:
        if not remote_id.strip():
            raise ValueError("remote publication ID is required")
        return self._transition(
            job_key, status="published", remote_id=remote_id, now=now
        )

    def retry(
        self,
        job_key: str,
        *,
        error_code: str,
        next_attempt_at: datetime,
        now: datetime,
    ) -> PublicationJob:
        return self._transition(
            job_key,
            status="retryable",
            error_code=error_code,
            next_attempt_at=next_attempt_at,
            now=now,
        )

    def fail(self, job_key: str, *, error_code: str, now: datetime) -> PublicationJob:
        return self._transition(
            job_key, status="failed", error_code=error_code, now=now
        )


class PublicationCoordinator:
    def __init__(self, store: PublicationStore, *, max_attempts: int = 5) -> None:
        if max_attempts < 1:
            raise ValueError("max attempts must be positive")
        self.store = store
        self.max_attempts = max_attempts

    @staticmethod
    def job_key(command: PublishCommand, platform: Platform) -> str:
        return f"{command.candidate_id}:{platform.value}:{command.artifact_sha256}"

    def execute(
        self,
        command: PublishCommand,
        platform: Platform,
        publisher: PublisherCall,
        *,
        now: datetime,
        retry_at: datetime,
    ) -> PublicationJob:
        claim = self.store.claim(
            job_key=self.job_key(command, platform),
            candidate_id=command.candidate_id,
            platform=platform,
            artifact_sha256=command.artifact_sha256,
            now=now,
        )
        if not claim.acquired:
            return claim.job
        try:
            result = publisher(command)
        except PlatformPending:
            return self.store.retry(
                claim.job.job_key,
                error_code="platform_processing_pending",
                next_attempt_at=retry_at,
                now=now,
            )
        except PlatformApiError as exc:
            retryable = exc.status_code in {0, 408, 409, 425, 429} or exc.status_code >= 500
            if retryable and claim.job.attempts < self.max_attempts:
                return self.store.retry(
                    claim.job.job_key,
                    error_code=exc.code,
                    next_attempt_at=retry_at,
                    now=now,
                )
            return self.store.fail(claim.job.job_key, error_code=exc.code, now=now)
        if result.platform != platform:
            return self.store.fail(
                claim.job.job_key, error_code="platform_result_mismatch", now=now
            )
        return self.store.complete(
            claim.job.job_key, remote_id=result.remote_id, now=now
        )

