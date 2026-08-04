from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from medibot.platforms import (
    Platform,
    PlatformApiError,
    PlatformPending,
    PublicationResult,
    PublishCommand,
)
from medibot.publication import PublicationCoordinator, PublicationStore


def command(tmp_path: Path) -> PublishCommand:
    path = tmp_path / "video.mp4"
    payload = b"\x00\x00\x00\x18ftypmp42" + b"x" * 2_000
    path.write_bytes(payload)
    return PublishCommand(
        "video-1",
        path,
        sha256(payload).hexdigest(),
        "Title",
        "Caption",
        "publish-1",
        "review-1",
        True,
    )


def test_store_claim_is_idempotent_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "jobs.db"
    first = PublicationStore(path)
    second = PublicationStore(path)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    values = {
        "job_key": "one",
        "candidate_id": "video",
        "platform": Platform.YOUTUBE,
        "artifact_sha256": "a" * 64,
        "now": now,
    }
    claim_one = first.claim(**values)
    claim_two = second.claim(**{**values, "job_key": "different"})

    assert claim_one.acquired is True
    assert claim_two.acquired is False
    assert claim_two.job.job_key == "one"
    assert claim_two.job.attempts == 1


def test_coordinator_completes_once_without_duplicate_call(tmp_path: Path) -> None:
    item = command(tmp_path)
    coordinator = PublicationCoordinator(PublicationStore(tmp_path / "jobs.db"))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    calls = 0

    def publish(_command: PublishCommand) -> PublicationResult:
        nonlocal calls
        calls += 1
        return PublicationResult(Platform.YOUTUBE, "remote-1", "published")

    first = coordinator.execute(
        item, Platform.YOUTUBE, publish, now=now, retry_at=now + timedelta(minutes=5)
    )
    second = coordinator.execute(
        item, Platform.YOUTUBE, publish, now=now, retry_at=now + timedelta(minutes=5)
    )
    assert first.status == second.status == "published"
    assert first.remote_id == "remote-1"
    assert calls == 1


def test_coordinator_retries_pending_and_transient_failure(tmp_path: Path) -> None:
    item = command(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    retry_at = now + timedelta(minutes=5)
    coordinator = PublicationCoordinator(PublicationStore(tmp_path / "jobs.db"))

    def pending(_command: PublishCommand) -> PublicationResult:
        raise PlatformPending("processing")

    first = coordinator.execute(
        item, Platform.X, pending, now=now, retry_at=retry_at
    )
    assert first.status == "retryable"
    assert first.next_attempt_at == retry_at

    def transient(_command: PublishCommand) -> PublicationResult:
        raise PlatformApiError(Platform.X, 503, "unavailable")

    before_retry = coordinator.execute(
        item, Platform.X, transient, now=now, retry_at=retry_at
    )
    assert before_retry.attempts == 1
    retried = coordinator.execute(
        item,
        Platform.X,
        transient,
        now=retry_at,
        retry_at=retry_at + timedelta(minutes=5),
    )
    assert retried.status == "retryable"
    assert retried.attempts == 2


def test_coordinator_fails_permanent_mismatch_and_attempt_limit(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = command(tmp_path)

    permanent = PublicationCoordinator(PublicationStore(tmp_path / "permanent.db"))
    failed = permanent.execute(
        item,
        Platform.FACEBOOK,
        lambda _item: (_ for _ in ()).throw(
            PlatformApiError(Platform.FACEBOOK, 400, "invalid_media")
        ),
        now=now,
        retry_at=now + timedelta(minutes=1),
    )
    assert failed.status == "failed"
    assert failed.last_error_code == "invalid_media"

    mismatch = PublicationCoordinator(PublicationStore(tmp_path / "mismatch.db"))
    mismatch_job = mismatch.execute(
        item,
        Platform.FACEBOOK,
        lambda _item: PublicationResult(Platform.X, "remote", "published"),
        now=now,
        retry_at=now + timedelta(minutes=1),
    )
    assert mismatch_job.status == "failed"
    assert mismatch_job.last_error_code == "platform_result_mismatch"

    limited = PublicationCoordinator(
        PublicationStore(tmp_path / "limited.db"), max_attempts=1
    )
    limited_job = limited.execute(
        item,
        Platform.X,
        lambda _item: (_ for _ in ()).throw(
            PlatformApiError(Platform.X, 503, "down")
        ),
        now=now,
        retry_at=now + timedelta(minutes=1),
    )
    assert limited_job.status == "failed"


def test_store_validates_transitions_and_job_identity(tmp_path: Path) -> None:
    store = PublicationStore(tmp_path / "jobs.db")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="identity"):
        store.claim(
            job_key="",
            candidate_id="one",
            platform=Platform.X,
            artifact_sha256="short",
            now=now,
        )
    claim = store.claim(
        job_key="one",
        candidate_id="one",
        platform=Platform.X,
        artifact_sha256="a" * 64,
        now=now,
    )
    with pytest.raises(ValueError, match="remote publication"):
        store.complete(claim.job.job_key, remote_id="", now=now)
    completed = store.complete(claim.job.job_key, remote_id="remote", now=now)
    assert completed.status == "published"
    with pytest.raises(ValueError, match="not in progress"):
        store.fail(claim.job.job_key, error_code="again", now=now)
    with pytest.raises(ValueError, match="max attempts"):
        PublicationCoordinator(store, max_attempts=0)

