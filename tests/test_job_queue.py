from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from medibot.job_queue import (
    DurableAutomationWorker,
    DurableJobQueue,
    JobKind,
    JobStatus,
    PermanentJobError,
    RetryableJobError,
)

NOW = datetime(2026, 8, 5, 8, tzinfo=UTC)


def test_enqueue_is_idempotent_and_rejects_secrets(tmp_path: Path) -> None:
    queue = DurableJobQueue(tmp_path / "jobs.sqlite3")
    first = queue.enqueue(
        JobKind.RENDER,
        {"candidate_id": "video-1", "duration": 30},
        idempotency_key="render:video-1",
        now=NOW,
    )
    same = queue.enqueue(
        JobKind.RENDER,
        {"candidate_id": "video-1", "duration": 30},
        idempotency_key="render:video-1",
        now=NOW,
    )

    assert first == same
    assert first.status == JobStatus.QUEUED
    with pytest.raises(ValueError, match="different job"):
        queue.enqueue(
            JobKind.PUBLISH,
            {"candidate_id": "video-1"},
            idempotency_key="render:video-1",
            now=NOW,
        )
    with pytest.raises(ValueError, match="credentials"):
        queue.enqueue(
            JobKind.PUBLISH,
            {"platform": "youtube", "access_token": "must-not-persist"},
            idempotency_key="publish:video-1",
            now=NOW,
        )


def test_claim_is_exclusive_and_expired_lease_is_recovered(tmp_path: Path) -> None:
    path = tmp_path / "jobs.sqlite3"
    first_queue = DurableJobQueue(path)
    second_queue = DurableJobQueue(path)
    queued = first_queue.enqueue(
        JobKind.RENDER,
        {"candidate_id": "video-1"},
        idempotency_key="render:video-1",
        now=NOW,
    )

    first = first_queue.claim(worker_id="worker-a", now=NOW, lease_for=timedelta(seconds=60))
    blocked = second_queue.claim(
        worker_id="worker-b",
        now=NOW + timedelta(seconds=30),
        lease_for=timedelta(seconds=60),
    )
    recovered = second_queue.claim(
        worker_id="worker-b",
        now=NOW + timedelta(seconds=61),
        lease_for=timedelta(seconds=60),
    )

    assert first is not None and first.job_id == queued.job_id
    assert blocked is None
    assert recovered is not None
    assert recovered.job_id == queued.job_id
    assert recovered.attempts == 2
    with pytest.raises(ValueError, match="does not own"):
        first_queue.complete(
            queued.job_id,
            worker_id="worker-a",
            result={},
            now=NOW + timedelta(seconds=62),
        )
    completed = second_queue.complete(
        queued.job_id,
        worker_id="worker-b",
        result={"artifact_sha256": "a" * 64},
        now=NOW + timedelta(seconds=62),
    )
    assert completed.status == JobStatus.COMPLETED
    assert completed.result == {"artifact_sha256": "a" * 64}


def test_retry_wait_attempt_limit_heartbeat_and_cancel(tmp_path: Path) -> None:
    queue = DurableJobQueue(tmp_path / "jobs.sqlite3")
    queued = queue.enqueue(
        JobKind.COLLECT_INSIGHTS,
        {"candidate_id": "video-1", "platform": "youtube"},
        idempotency_key="insights:video-1:youtube",
        now=NOW,
        max_attempts=2,
    )
    claimed = queue.claim(worker_id="worker-a", now=NOW)
    assert claimed is not None
    heartbeat = queue.heartbeat(
        claimed.job_id,
        worker_id="worker-a",
        now=NOW + timedelta(seconds=10),
        lease_for=timedelta(minutes=20),
    )
    assert heartbeat.lease_expires_at == NOW + timedelta(minutes=20, seconds=10)
    retry_at = NOW + timedelta(minutes=2)
    waiting = queue.retry(
        claimed.job_id,
        worker_id="worker-a",
        error_code="platform_busy",
        available_at=retry_at,
        now=NOW + timedelta(seconds=11),
    )
    assert waiting.status == JobStatus.RETRY_WAIT
    assert queue.claim(worker_id="worker-b", now=retry_at - timedelta(seconds=1)) is None
    second = queue.claim(worker_id="worker-b", now=retry_at)
    assert second is not None and second.attempts == 2
    exhausted = queue.retry(
        second.job_id,
        worker_id="worker-b",
        error_code="platform_busy",
        available_at=retry_at + timedelta(minutes=2),
        now=retry_at + timedelta(seconds=1),
    )
    assert exhausted.status == JobStatus.FAILED
    assert exhausted.error_code == "attempt_limit_reached"

    cancelled_source = queue.enqueue(
        JobKind.MIRROR_ARTIFACT,
        {"artifact_key": "previews/video-2/preview.mp4"},
        idempotency_key="mirror:video-2",
        now=NOW,
    )
    cancelled = queue.cancel(cancelled_source.job_id, now=NOW)
    assert cancelled.status == JobStatus.CANCELLED
    with pytest.raises(ValueError, match="queued"):
        queue.cancel(queued.job_id, now=NOW)


def test_worker_completes_retries_and_sanitizes_unknown_failures(tmp_path: Path) -> None:
    queue = DurableJobQueue(tmp_path / "jobs.sqlite3")
    current = [NOW]

    queue.enqueue(
        JobKind.RENDER,
        {"candidate_id": "video-1"},
        idempotency_key="render:video-1",
        now=NOW,
    )
    worker = DurableAutomationWorker(
        queue,
        worker_id="worker-a",
        handlers={JobKind.RENDER: lambda job: {"candidate_id": job.payload["candidate_id"]}},
        clock=lambda: current[0],
    )
    completed = worker.run_once()
    assert completed is not None
    assert completed.status == JobStatus.COMPLETED
    assert completed.result == {"candidate_id": "video-1"}

    queue.enqueue(
        JobKind.PUBLISH,
        {"candidate_id": "video-2"},
        idempotency_key="publish:video-2",
        now=NOW,
        max_attempts=2,
    )

    def transient(_job):
        raise RetryableJobError("platform_busy", timedelta(minutes=3))

    retry_worker = DurableAutomationWorker(
        queue,
        worker_id="worker-b",
        handlers={JobKind.PUBLISH: transient},
        clock=lambda: current[0],
    )
    waiting = retry_worker.run_once()
    assert waiting is not None and waiting.status == JobStatus.RETRY_WAIT
    current[0] += timedelta(minutes=3)
    exhausted = retry_worker.run_once()
    assert exhausted is not None and exhausted.status == JobStatus.FAILED
    assert exhausted.error_code == "attempt_limit_reached"

    queue.enqueue(
        JobKind.COLLECT_INSIGHTS,
        {"candidate_id": "video-3"},
        idempotency_key="insights:video-3",
        now=current[0],
    )
    unavailable = DurableAutomationWorker(
        queue,
        worker_id="worker-c",
        handlers={},
        clock=lambda: current[0],
    ).run_once()
    assert unavailable is not None
    assert unavailable.status == JobStatus.FAILED
    assert unavailable.error_code == "handler_unavailable"


def test_worker_permanent_and_unhandled_errors_are_bounded(tmp_path: Path) -> None:
    queue = DurableJobQueue(tmp_path / "jobs.sqlite3")
    current = [NOW]
    queue.enqueue(
        JobKind.RENDER,
        {"candidate_id": "video-1"},
        idempotency_key="render:video-1",
        now=NOW,
    )
    permanent = DurableAutomationWorker(
        queue,
        worker_id="worker-a",
        handlers={
            JobKind.RENDER: lambda _job: (_ for _ in ()).throw(PermanentJobError("invalid_source"))
        },
        clock=lambda: current[0],
    ).run_once()
    assert permanent is not None
    assert permanent.status == JobStatus.FAILED
    assert permanent.error_code == "invalid_source"

    queue.enqueue(
        JobKind.PUBLISH,
        {"candidate_id": "video-2"},
        idempotency_key="publish:video-2",
        now=NOW,
    )

    def exploding(_job):
        raise RuntimeError("private dependency details")

    bounded = DurableAutomationWorker(
        queue,
        worker_id="worker-b",
        handlers={JobKind.PUBLISH: exploding},
        clock=lambda: current[0],
    ).run_once()
    assert bounded is not None
    assert bounded.status == JobStatus.RETRY_WAIT
    assert bounded.error_code == "unhandled_job_error"
    assert "private" not in str(bounded)


def test_queue_validates_time_identity_data_and_batch_limits(tmp_path: Path) -> None:
    queue = DurableJobQueue(tmp_path / "jobs.sqlite3")
    with pytest.raises(ValueError, match="timezone"):
        queue.enqueue(
            JobKind.RENDER,
            {},
            idempotency_key="render:one",
            now=datetime(2026, 1, 1),
        )
    with pytest.raises(ValueError, match="JSON"):
        queue.enqueue(
            JobKind.RENDER,
            {"bad": object()},
            idempotency_key="render:one",
            now=NOW,
        )
    with pytest.raises(ValueError, match="JSON"):
        queue.enqueue(
            JobKind.RENDER,
            {"not_json": float("nan")},
            idempotency_key="render:nan",
            now=NOW,
        )
    with pytest.raises(ValueError, match="64 KiB"):
        queue.enqueue(
            JobKind.RENDER,
            {"large": "x" * (65 * 1024)},
            idempotency_key="render:large",
            now=NOW,
        )
    with pytest.raises(ValueError, match="worker ID"):
        queue.claim(worker_id="bad worker", now=NOW)

    worker = DurableAutomationWorker(
        queue,
        worker_id="worker-a",
        handlers={},
        clock=lambda: NOW,
    )
    with pytest.raises(ValueError, match="batch limit"):
        worker.run_until_idle(max_jobs=0)
    assert queue.get("a" * 32) is None
    assert queue.counts() == {}


def test_queue_normalizes_offsets_to_utc_and_heartbeat_never_shortens_lease(
    tmp_path: Path,
) -> None:
    queue = DurableJobQueue(tmp_path / "jobs.sqlite3")
    pakistan_time = datetime(2026, 8, 5, 13, tzinfo=timezone(timedelta(hours=5)))
    queued = queue.enqueue(
        JobKind.RENDER,
        {"candidate_id": "video-1"},
        idempotency_key="render:video-1",
        now=pakistan_time,
    )
    assert queued.created_at == NOW
    assert queued.created_at.tzinfo == UTC

    claimed = queue.claim(
        worker_id="worker-a",
        now=pakistan_time,
        lease_for=timedelta(minutes=20),
    )
    assert claimed is not None
    original_expiry = claimed.lease_expires_at
    heartbeat = queue.heartbeat(
        claimed.job_id,
        worker_id="worker-a",
        now=NOW + timedelta(minutes=1),
        lease_for=timedelta(minutes=5),
    )
    assert heartbeat.lease_expires_at == original_expiry
