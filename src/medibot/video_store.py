"""SQLite persistence for the self-learning video system."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from medibot.video_system import (
    DatasetCatalog,
    DomainGuard,
    DomainProfile,
    PerformanceInsight,
    ScheduleDecision,
    VideoCandidate,
)

_SCHEMA_VERSION = 1


class VideoStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS domain_profiles (
                    profile_name TEXT PRIMARY KEY,
                    allowed_topics TEXT NOT NULL,
                    allowed_keywords TEXT NOT NULL,
                    blocked_keywords TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS videos (
                    candidate_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL,
                    script TEXT NOT NULL,
                    source_path TEXT,
                    duration_seconds REAL,
                    language TEXT NOT NULL,
                    style_tags TEXT NOT NULL,
                    asset_sha256 TEXT,
                    content_hash TEXT NOT NULL UNIQUE,
                    imported_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'imported'
                        CHECK (status IN ('imported', 'planned', 'rendered', 'approved',
                                          'scheduled', 'published', 'failed'))
                );

                CREATE TABLE IF NOT EXISTS insights (
                    insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL REFERENCES videos(candidate_id),
                    platform TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    impressions INTEGER NOT NULL CHECK (impressions >= 0),
                    views INTEGER NOT NULL CHECK (views >= 0),
                    average_watch_ratio REAL NOT NULL,
                    likes INTEGER NOT NULL CHECK (likes >= 0),
                    comments INTEGER NOT NULL CHECK (comments >= 0),
                    shares INTEGER NOT NULL CHECK (shares >= 0),
                    UNIQUE(candidate_id, platform, collected_at)
                );

                CREATE TABLE IF NOT EXISTS schedule_decisions (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL REFERENCES videos(candidate_id),
                    publish_at TEXT NOT NULL,
                    score REAL NOT NULL,
                    reasons TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(candidate_id, publish_at)
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (?, ?)",
                (_SCHEMA_VERSION, datetime.now().astimezone().isoformat()),
            )

    def save_domain_profile(self, profile: DomainProfile, *, updated_at: datetime) -> None:
        DomainGuard(profile)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO domain_profiles(
                    profile_name, allowed_topics, allowed_keywords, blocked_keywords, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_name) DO UPDATE SET
                    allowed_topics=excluded.allowed_topics,
                    allowed_keywords=excluded.allowed_keywords,
                    blocked_keywords=excluded.blocked_keywords,
                    updated_at=excluded.updated_at
                """,
                (
                    profile.name,
                    json.dumps(sorted(profile.allowed_topics)),
                    json.dumps(sorted(profile.allowed_keywords)),
                    json.dumps(sorted(profile.blocked_keywords)),
                    updated_at.isoformat(),
                ),
            )

    def get_domain_profile(self, name: str) -> DomainProfile | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM domain_profiles WHERE profile_name = ?", (name,)
            ).fetchone()
        if row is None:
            return None
        return DomainProfile(
            name=row["profile_name"],
            allowed_topics=frozenset(json.loads(row["allowed_topics"])),
            allowed_keywords=frozenset(json.loads(row["allowed_keywords"])),
            blocked_keywords=frozenset(json.loads(row["blocked_keywords"])),
        )

    def register_candidates(
        self,
        profile: DomainProfile,
        candidates: list[VideoCandidate],
        *,
        imported_at: datetime,
    ) -> int:
        guard = DomainGuard(profile)
        catalog = DatasetCatalog(guard)
        prepared = [catalog.register(item, imported_at=imported_at) for item in candidates]
        with self._connection() as connection:
            for candidate, digest, stamp in prepared:
                connection.execute(
                    """
                    INSERT INTO videos(
                        candidate_id, topic, title, script, source_path, duration_seconds,
                        language, style_tags, asset_sha256, content_hash, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candidate.candidate_id,
                        candidate.topic,
                        candidate.title,
                        candidate.script,
                        candidate.source_path,
                        candidate.duration_seconds,
                        candidate.language,
                        json.dumps(list(candidate.style_tags)),
                        candidate.asset_sha256,
                        digest,
                        stamp.isoformat(),
                    ),
                )
        return len(prepared)

    def list_candidates(self, *, status: str | None = None) -> list[VideoCandidate]:
        query = "SELECT * FROM videos"
        params: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY imported_at, candidate_id"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            VideoCandidate(
                candidate_id=row["candidate_id"],
                topic=row["topic"],
                title=row["title"],
                script=row["script"],
                source_path=row["source_path"],
                duration_seconds=row["duration_seconds"],
                language=row["language"],
                style_tags=tuple(json.loads(row["style_tags"])),
                asset_sha256=row["asset_sha256"],
            )
            for row in rows
        ]

    def set_video_status(self, candidate_id: str, status: str) -> None:
        allowed = {
            "imported", "planned", "rendered", "approved",
            "scheduled", "published", "failed",
        }
        if status not in allowed:
            raise ValueError("unknown video status")
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE videos SET status = ? WHERE candidate_id = ?", (status, candidate_id)
            )
            if cursor.rowcount != 1:
                raise KeyError(candidate_id)

    def add_insight(
        self,
        candidate_id: str,
        platform: str,
        insight: PerformanceInsight,
        *,
        collected_at: datetime,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO insights(
                    candidate_id, platform, collected_at, published_at, impressions, views,
                    average_watch_ratio, likes, comments, shares
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    platform,
                    collected_at.isoformat(),
                    insight.published_at.isoformat(),
                    insight.impressions,
                    insight.views,
                    insight.average_watch_ratio,
                    insight.likes,
                    insight.comments,
                    insight.shares,
                ),
            )

    def list_insights(self) -> list[PerformanceInsight]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT videos.topic, insights.* FROM insights
                JOIN videos USING(candidate_id)
                ORDER BY published_at
                """
            ).fetchall()
        return [
            PerformanceInsight(
                topic=row["topic"],
                published_at=datetime.fromisoformat(row["published_at"]),
                impressions=row["impressions"],
                views=row["views"],
                average_watch_ratio=row["average_watch_ratio"],
                likes=row["likes"],
                comments=row["comments"],
                shares=row["shares"],
            )
            for row in rows
        ]

    def record_schedule_decision(
        self, decision: ScheduleDecision, *, created_at: datetime
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO schedule_decisions(
                    candidate_id, publish_at, score, reasons, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    decision.candidate_id,
                    decision.publish_at.isoformat(),
                    decision.score,
                    json.dumps(list(decision.reasons)),
                    created_at.isoformat(),
                ),
            )

    def list_publish_times(self) -> list[datetime]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT publish_at FROM schedule_decisions ORDER BY publish_at"
            ).fetchall()
        return [datetime.fromisoformat(row["publish_at"]) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connection() as connection:
            videos = connection.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            insights = connection.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
            decisions = connection.execute(
                "SELECT COUNT(*) FROM schedule_decisions"
            ).fetchone()[0]
        return {"videos": videos, "insights": insights, "decisions": decisions}




