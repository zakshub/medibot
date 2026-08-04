"""Durable SQLite leases for rendering, publishing, and insight jobs."""

import json
import re
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import uuid4

_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,199}$")
_ERROR_CODE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")
_MAX_JSON_BYTES = 64 * 1024
_SECRET_NAMES = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "credentials",
        "password",
        "secret",
        "access_token",
        "refresh_token",
    }
)


class JobKind(StrEnum):
    RENDER = "render"
    PUBLISH = "publish"
    COLLECT_INSIGHTS = "collect_insights"
    MIRROR_ARTIFACT = "mirror_artifact"


class JobStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    kind: JobKind
    payload: dict[str, object]
    idempotency_key: str
    status: JobStatus
    attempts: int
    max_attempts: int
    available_at: datetime
    lease_owner: str | None
    lease_expires_at: datetime | None
    result: dict[str, object] | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class JobHandler(Protocol):
    def __call__(self, job: JobRecord) -> dict[str, object] | None: ...


class RetryableJobError(RuntimeError):
    def __init__(self, code: str, retry_after: timedelta) -> None:
        _validate_error_code(code)
        if retry_after <= timedelta(0) or retry_after > timedelta(days=1):
            raise ValueError("retry delay must be between zero and one day")
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


class PermanentJobError(RuntimeError):
    def __init__(self, code: str) -> None:
        _validate_error_code(code)
        super().__init__(code)
        self.code = code


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("job timestamps must include a timezone")
    return value.astimezone(UTC)


def _validate_identity(value: str, label: str) -> None:
    if not _IDENTITY.fullmatch(value):
        raise ValueError(f"{label} is invalid")


def _validate_error_code(value: str) -> None:
    if not _ERROR_CODE.fullmatch(value):
        raise ValueError("job error code is invalid")


def _reject_secrets(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().casefold().replace("-", "_")
            if normalized in _SECRET_NAMES or normalized.endswith(
                ("_password", "_secret", "_token", "_api_key")
            ):
                raise ValueError("job payloads and results cannot contain credentials")
            _reject_secrets(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_secrets(child)


def _encode_json(value: Mapping[str, object]) -> str:
    _reject_secrets(dict(value))
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("job data must be JSON serializable") from exc
    if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
        raise ValueError("job data exceeds 64 KiB")
    return encoded


class DurableJobQueue:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS automation_jobs (
                    job_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK(
                        kind IN ('render', 'publish', 'collect_insights', 'mirror_artifact')
                    ),
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK(
                        status IN (
                            'queued', 'leased', 'retry_wait',
                            'completed', 'failed', 'cancelled'
                        )
                    ),
                    attempts INTEGER NOT NULL CHECK(attempts >= 0),
                    max_attempts INTEGER NOT NULL CHECK(max_attempts BETWEEN 1 AND 20),
                    available_at TEXT NOT NULL,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    result_json TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_automation_jobs_claim
                    ON automation_jobs(status, available_at, lease_expires_at);
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
    def _from_row(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            row["job_id"],
            JobKind(row["kind"]),
            json.loads(row["payload_json"]),
            row["idempotency_key"],
            JobStatus(row["status"]),
            row["attempts"],
            row["max_attempts"],
            datetime.fromisoformat(row["available_at"]),
            row["lease_owner"],
            datetime.fromisoformat(row["lease_expires_at"]) if row["lease_expires_at"] else None,
            json.loads(row["result_json"]) if row["result_json"] else None,
            row["error_code"],
            datetime.fromisoformat(row["created_at"]),
            datetime.fromisoformat(row["updated_at"]),
        )

    def enqueue(
        self,
        kind: JobKind,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        now: datetime,
        available_at: datetime | None = None,
        max_attempts: int = 5,
    ) -> JobRecord:
        _validate_identity(idempotency_key, "job idempotency key")
        now = _as_utc(now)
        available = _as_utc(available_at or now)
        if not 1 <= max_attempts <= 20:
            raise ValueError("job max attempts must be between 1 and 20")
        payload_json = _encode_json(payload)
        job_id = uuid4().hex
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO automation_jobs(
                        job_id, kind, payload_json, idempotency_key, status,
                        attempts, max_attempts, available_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'queued', 0, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        kind.value,
                        payload_json,
                        idempotency_key,
                        max_attempts,
                        available.isoformat(),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM automation_jobs WHERE idempotency_key=?",
                    (idempotency_key,),
                ).fetchone()
                if row["kind"] != kind.value or row["payload_json"] != payload_json:
                    raise ValueError("idempotency key already belongs to a different job")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self._from_row(row)

    def claim(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_for: timedelta = timedelta(minutes=10),
    ) -> JobRecord | None:
        _validate_identity(worker_id, "worker ID")
        now = _as_utc(now)
        if not timedelta(seconds=30) <= lease_for <= timedelta(hours=1):
            raise ValueError("job lease must be between 30 seconds and one hour")
        expiry = now + lease_for
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    UPDATE automation_jobs
                    SET status='failed', error_code='lease_expired_attempt_limit',
                        lease_owner=NULL, lease_expires_at=NULL, updated_at=?
                    WHERE status='leased' AND lease_expires_at <= ?
                      AND attempts >= max_attempts
                    """,
                    (now.isoformat(), now.isoformat()),
                )
                row = connection.execute(
                    """
                    SELECT * FROM automation_jobs
                    WHERE attempts < max_attempts AND (
                        (status IN ('queued', 'retry_wait') AND available_at <= ?)
                        OR (status='leased' AND lease_expires_at <= ?)
                    )
                    ORDER BY available_at, created_at, job_id
                    LIMIT 1
                    """,
                    (now.isoformat(), now.isoformat()),
                ).fetchone()
                if row is None:
                    connection.commit()
                    return None
                connection.execute(
                    """
                    UPDATE automation_jobs
                    SET status='leased', attempts=attempts+1, lease_owner=?,
                        lease_expires_at=?, error_code=NULL, updated_at=?
                    WHERE job_id=?
                    """,
                    (worker_id, expiry.isoformat(), now.isoformat(), row["job_id"]),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            current = connection.execute(
                "SELECT * FROM automation_jobs WHERE job_id=?", (row["job_id"],)
            ).fetchone()
        return self._from_row(current)

    def _owned_lease(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        worker_id: str,
        now: datetime,
    ) -> sqlite3.Row:
        _validate_identity(job_id, "job ID")
        _validate_identity(worker_id, "worker ID")
        _as_utc(now)
        row = connection.execute(
            """
            SELECT * FROM automation_jobs
            WHERE job_id=? AND status='leased' AND lease_owner=? AND lease_expires_at > ?
            """,
            (job_id, worker_id, now.isoformat()),
        ).fetchone()
        if row is None:
            raise ValueError("worker does not own an active job lease")
        return row

    def heartbeat(
        self,
        job_id: str,
        *,
        worker_id: str,
        now: datetime,
        lease_for: timedelta = timedelta(minutes=10),
    ) -> JobRecord:
        now = _as_utc(now)
        if not timedelta(seconds=30) <= lease_for <= timedelta(hours=1):
            raise ValueError("job lease must be between 30 seconds and one hour")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                current = self._owned_lease(connection, job_id, worker_id, now)
                existing_expiry = datetime.fromisoformat(current["lease_expires_at"])
                new_expiry = max(existing_expiry, now + lease_for)
                connection.execute(
                    """
                    UPDATE automation_jobs SET lease_expires_at=?, updated_at=?
                    WHERE job_id=?
                    """,
                    (new_expiry.isoformat(), now.isoformat(), job_id),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            row = connection.execute(
                "SELECT * FROM automation_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        return self._from_row(row)

    def complete(
        self,
        job_id: str,
        *,
        worker_id: str,
        result: Mapping[str, object] | None,
        now: datetime,
    ) -> JobRecord:
        result_json = _encode_json(result or {})
        return self._finish_owned(
            job_id,
            worker_id=worker_id,
            now=now,
            status=JobStatus.COMPLETED,
            result_json=result_json,
        )

    def fail(
        self,
        job_id: str,
        *,
        worker_id: str,
        error_code: str,
        now: datetime,
    ) -> JobRecord:
        _validate_error_code(error_code)
        return self._finish_owned(
            job_id,
            worker_id=worker_id,
            now=now,
            status=JobStatus.FAILED,
            error_code=error_code,
        )

    def _finish_owned(
        self,
        job_id: str,
        *,
        worker_id: str,
        now: datetime,
        status: JobStatus,
        result_json: str | None = None,
        error_code: str | None = None,
    ) -> JobRecord:
        now = _as_utc(now)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._owned_lease(connection, job_id, worker_id, now)
                connection.execute(
                    """
                    UPDATE automation_jobs
                    SET status=?, result_json=?, error_code=?, lease_owner=NULL,
                        lease_expires_at=NULL, updated_at=?
                    WHERE job_id=?
                    """,
                    (status.value, result_json, error_code, now.isoformat(), job_id),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            row = connection.execute(
                "SELECT * FROM automation_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        return self._from_row(row)

    def retry(
        self,
        job_id: str,
        *,
        worker_id: str,
        error_code: str,
        available_at: datetime,
        now: datetime,
    ) -> JobRecord:
        _validate_error_code(error_code)
        now = _as_utc(now)
        available_at = _as_utc(available_at)
        if available_at <= now:
            raise ValueError("retry availability must be in the future")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                current = self._owned_lease(connection, job_id, worker_id, now)
                if current["attempts"] >= current["max_attempts"]:
                    status = JobStatus.FAILED
                    stored_error = "attempt_limit_reached"
                else:
                    status = JobStatus.RETRY_WAIT
                    stored_error = error_code
                connection.execute(
                    """
                    UPDATE automation_jobs
                    SET status=?, available_at=?, error_code=?, lease_owner=NULL,
                        lease_expires_at=NULL, updated_at=?
                    WHERE job_id=?
                    """,
                    (
                        status.value,
                        available_at.isoformat(),
                        stored_error,
                        now.isoformat(),
                        job_id,
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            row = connection.execute(
                "SELECT * FROM automation_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        return self._from_row(row)

    def cancel(self, job_id: str, *, now: datetime) -> JobRecord:
        _validate_identity(job_id, "job ID")
        now = _as_utc(now)
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE automation_jobs
                SET status='cancelled', updated_at=?
                WHERE job_id=? AND status IN ('queued', 'retry_wait')
                """,
                (now.isoformat(), job_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("only queued or retry-wait jobs can be cancelled")
            row = connection.execute(
                "SELECT * FROM automation_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        return self._from_row(row)

    def get(self, job_id: str) -> JobRecord | None:
        _validate_identity(job_id, "job ID")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM automation_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def counts(self) -> dict[str, int]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS total FROM automation_jobs GROUP BY status"
            ).fetchall()
        return {row["status"]: row["total"] for row in rows}


class DurableAutomationWorker:
    def __init__(
        self,
        queue: DurableJobQueue,
        *,
        worker_id: str,
        handlers: Mapping[JobKind, JobHandler],
        clock: Callable[[], datetime],
        lease_for: timedelta = timedelta(minutes=10),
        default_retry_after: timedelta = timedelta(minutes=5),
    ) -> None:
        _validate_identity(worker_id, "worker ID")
        if not timedelta(seconds=30) <= lease_for <= timedelta(hours=1):
            raise ValueError("job lease must be between 30 seconds and one hour")
        if default_retry_after <= timedelta(0) or default_retry_after > timedelta(days=1):
            raise ValueError("default retry delay must be between zero and one day")
        self.queue = queue
        self.worker_id = worker_id
        self.handlers = dict(handlers)
        self.clock = clock
        self.lease_for = lease_for
        self.default_retry_after = default_retry_after

    def run_once(self) -> JobRecord | None:
        job = self.queue.claim(
            worker_id=self.worker_id,
            now=self.clock(),
            lease_for=self.lease_for,
        )
        if job is None:
            return None
        handler = self.handlers.get(job.kind)
        if handler is None:
            return self.queue.fail(
                job.job_id,
                worker_id=self.worker_id,
                error_code="handler_unavailable",
                now=self.clock(),
            )
        try:
            result = handler(job)
        except PermanentJobError as exc:
            return self.queue.fail(
                job.job_id,
                worker_id=self.worker_id,
                error_code=exc.code,
                now=self.clock(),
            )
        except RetryableJobError as exc:
            now = self.clock()
            return self.queue.retry(
                job.job_id,
                worker_id=self.worker_id,
                error_code=exc.code,
                available_at=now + exc.retry_after,
                now=now,
            )
        except Exception:
            now = self.clock()
            return self.queue.retry(
                job.job_id,
                worker_id=self.worker_id,
                error_code="unhandled_job_error",
                available_at=now + self.default_retry_after,
                now=now,
            )
        return self.queue.complete(
            job.job_id,
            worker_id=self.worker_id,
            result=result,
            now=self.clock(),
        )

    def run_until_idle(self, *, max_jobs: int = 100) -> list[JobRecord]:
        if not 1 <= max_jobs <= 1_000:
            raise ValueError("worker batch limit must be between 1 and 1000")
        completed = []
        for _ in range(max_jobs):
            result = self.run_once()
            if result is None:
                break
            completed.append(result)
        return completed
