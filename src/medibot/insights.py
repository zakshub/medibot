"""Platform insight collection and normalization for the learning engine."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from medibot.learning import ContentVariant, LearningObservation
from medibot.platforms import ApiTransport, Platform, PlatformApiError


@dataclass(frozen=True, slots=True)
class NormalizedInsight:
    platform: Platform
    remote_id: str
    collected_at: datetime
    impressions: int
    views: int
    average_watch_ratio: float
    likes: int
    comments: int
    shares: int
    available_metrics: frozenset[str]

    def __post_init__(self) -> None:
        values = (
            self.impressions,
            self.views,
            self.likes,
            self.comments,
            self.shares,
        )
        if min(values) < 0:
            raise ValueError("normalized insight values cannot be negative")
        if not 0 <= self.average_watch_ratio <= 1:
            raise ValueError("watch ratio must be between zero and one")

    def to_learning_observation(self, variant: ContentVariant) -> LearningObservation:
        return LearningObservation.from_metrics(
            variant,
            impressions=self.impressions,
            views=self.views,
            average_watch_ratio=self.average_watch_ratio,
            likes=self.likes,
            comments=self.comments,
            shares=self.shares,
        )


def _integer(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _ratio(average_watch_seconds: object, duration_seconds: float) -> float:
    if duration_seconds <= 0:
        raise ValueError("video duration must be positive")
    try:
        value = float(average_watch_seconds)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return min(max(value / duration_seconds, 0.0), 1.0)


def _meta_values(payload: dict[str, Any]) -> dict[str, object]:
    result: dict[str, object] = {}
    for metric in payload.get("data", []):
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("name", ""))
        values = metric.get("values", [])
        if isinstance(values, list) and values and isinstance(values[0], dict):
            result[name] = values[0].get("value", 0)
        elif "value" in metric:
            result[name] = metric["value"]
    return result


class InsightNormalizer:
    @staticmethod
    def youtube(
        remote_id: str,
        payload: dict[str, Any],
        *,
        duration_seconds: float,
        collected_at: datetime,
    ) -> NormalizedInsight:
        headers = [
            str(item.get("name", ""))
            for item in payload.get("columnHeaders", [])
            if isinstance(item, dict)
        ]
        rows = payload.get("rows", [])
        row = rows[0] if isinstance(rows, list) and rows else []
        metrics = dict(zip(headers, row, strict=False))
        views = _integer(metrics.get("views"))
        impressions = _integer(metrics.get("videoThumbnailImpressions")) or views
        average_seconds = metrics.get("averageViewDuration", 0)
        available = frozenset(key for key in headers if key)
        return NormalizedInsight(
            Platform.YOUTUBE,
            remote_id,
            collected_at,
            impressions,
            views,
            _ratio(average_seconds, duration_seconds),
            _integer(metrics.get("likes")),
            _integer(metrics.get("comments")),
            _integer(metrics.get("shares")),
            available,
        )

    @staticmethod
    def instagram(
        remote_id: str,
        payload: dict[str, Any],
        *,
        duration_seconds: float,
        collected_at: datetime,
    ) -> NormalizedInsight:
        metrics = _meta_values(payload)
        views = _integer(
            metrics.get("views", metrics.get("ig_reels_aggregated_all_plays_count", 0))
        )
        impressions = _integer(metrics.get("reach", metrics.get("impressions", views))) or views
        watch_ms = metrics.get("ig_reels_avg_watch_time", 0)
        average_seconds = float(watch_ms or 0) / 1_000
        return NormalizedInsight(
            Platform.INSTAGRAM,
            remote_id,
            collected_at,
            impressions,
            views,
            _ratio(average_seconds, duration_seconds),
            _integer(metrics.get("likes")),
            _integer(metrics.get("comments")),
            _integer(metrics.get("shares")),
            frozenset(metrics),
        )

    @staticmethod
    def facebook(
        remote_id: str,
        payload: dict[str, Any],
        *,
        duration_seconds: float,
        collected_at: datetime,
    ) -> NormalizedInsight:
        metrics = _meta_values(payload)
        views = _integer(metrics.get("post_video_views", metrics.get("plays", 0)))
        impressions = _integer(metrics.get("post_impressions_unique", metrics.get("reach", 0)))
        impressions = impressions or views
        average_seconds = metrics.get("post_video_avg_time_watched", 0)
        return NormalizedInsight(
            Platform.FACEBOOK,
            remote_id,
            collected_at,
            impressions,
            views,
            _ratio(average_seconds, duration_seconds),
            _integer(metrics.get("reactions")),
            _integer(metrics.get("comments")),
            _integer(metrics.get("shares")),
            frozenset(metrics),
        )

    @staticmethod
    def x(
        remote_id: str,
        payload: dict[str, Any],
        *,
        duration_seconds: float,
        collected_at: datetime,
    ) -> NormalizedInsight:
        data = payload.get("data", {})
        public = data.get("public_metrics", {}) if isinstance(data, dict) else {}
        private = data.get("non_public_metrics", {}) if isinstance(data, dict) else {}
        metrics = {**public, **private}
        views = _integer(metrics.get("video_view_count", metrics.get("view_count", 0)))
        impressions = _integer(metrics.get("impression_count", views)) or views
        average_seconds = metrics.get("video_avg_view_time", 0)
        return NormalizedInsight(
            Platform.X,
            remote_id,
            collected_at,
            impressions,
            views,
            _ratio(average_seconds, duration_seconds),
            _integer(metrics.get("like_count")),
            _integer(metrics.get("reply_count")),
            _integer(metrics.get("retweet_count", metrics.get("repost_count", 0))),
            frozenset(metrics),
        )


class PlatformInsightClient:
    def __init__(self, transport: ApiTransport, *, meta_api_version: str = "v23.0") -> None:
        self.transport = transport
        self.meta_api_version = meta_api_version

    def _get(
        self,
        platform: Platform,
        url: str,
        *,
        token: str,
        params: dict[str, object],
    ) -> dict[str, Any]:
        response = self.transport.request("GET", url, token=token, params=params)
        if response.status_code != 200:
            raise PlatformApiError(platform, response.status_code, "insight_fetch_failed")
        return response.json_body

    def youtube(
        self,
        remote_id: str,
        *,
        token: str,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        return self._get(
            Platform.YOUTUBE,
            "https://youtubeanalytics.googleapis.com/v2/reports",
            token=token,
            params={
                "ids": "channel==MINE",
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": "video",
                "filters": f"video=={remote_id}",
                "metrics": (
                    "views,averageViewDuration,likes,comments,shares,"
                    "videoThumbnailImpressions"
                ),
            },
        )

    def instagram(self, remote_id: str, *, token: str) -> dict[str, Any]:
        return self._get(
            Platform.INSTAGRAM,
            f"https://graph.facebook.com/{self.meta_api_version}/{remote_id}/insights",
            token=token,
            params={
                "metric": (
                    "views,reach,likes,comments,shares,ig_reels_avg_watch_time,"
                    "ig_reels_aggregated_all_plays_count"
                )
            },
        )

    def facebook(self, remote_id: str, *, token: str) -> dict[str, Any]:
        return self._get(
            Platform.FACEBOOK,
            f"https://graph.facebook.com/{self.meta_api_version}/{remote_id}/video_insights",
            token=token,
            params={
                "metric": (
                    "post_video_views,post_impressions_unique,"
                    "post_video_avg_time_watched,reactions,comments,shares"
                )
            },
        )

    def x(self, remote_id: str, *, token: str) -> dict[str, Any]:
        return self._get(
            Platform.X,
            f"https://api.x.com/2/tweets/{remote_id}",
            token=token,
            params={"tweet.fields": "public_metrics,non_public_metrics"},
        )

