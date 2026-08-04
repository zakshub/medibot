from datetime import UTC, datetime
from typing import Any

import pytest

from medibot.insights import InsightNormalizer, NormalizedInsight, PlatformInsightClient
from medibot.learning import ContentVariant
from medibot.platforms import ApiResponse, Platform, PlatformApiError


class FakeTransport:
    def __init__(self, response: ApiResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: object) -> ApiResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.response


NOW = datetime(2026, 1, 2, tzinfo=UTC)


def test_youtube_normalization_and_learning_reward() -> None:
    payload = {
        "columnHeaders": [
            {"name": "views"},
            {"name": "averageViewDuration"},
            {"name": "likes"},
            {"name": "comments"},
            {"name": "shares"},
            {"name": "videoThumbnailImpressions"},
        ],
        "rows": [[80, 15, 10, 3, 2, 100]],
    }
    insight = InsightNormalizer.youtube(
        "yt-1", payload, duration_seconds=30, collected_at=NOW
    )
    assert insight.platform == Platform.YOUTUBE
    assert insight.views == 80
    assert insight.impressions == 100
    assert insight.average_watch_ratio == 0.5
    observation = insight.to_learning_observation(
        ContentVariant("sleep", 9, "explainer", "short")
    )
    assert 0 < observation.reward <= 1


def test_meta_normalizers_handle_metric_shapes() -> None:
    instagram = InsightNormalizer.instagram(
        "ig-1",
        {
            "data": [
                {"name": "views", "values": [{"value": 100}]},
                {"name": "reach", "values": [{"value": 80}]},
                {"name": "ig_reels_avg_watch_time", "values": [{"value": 15000}]},
                {"name": "shares", "values": [{"value": 5}]},
            ]
        },
        duration_seconds=30,
        collected_at=NOW,
    )
    assert instagram.views == 100
    assert instagram.impressions == 80
    assert instagram.average_watch_ratio == 0.5
    assert instagram.shares == 5

    facebook = InsightNormalizer.facebook(
        "fb-1",
        {
            "data": [
                {"name": "post_video_views", "value": 40},
                {"name": "post_video_avg_time_watched", "value": 10},
            ]
        },
        duration_seconds=20,
        collected_at=NOW,
    )
    assert facebook.views == facebook.impressions == 40
    assert facebook.average_watch_ratio == 0.5


def test_x_normalization_clamps_and_handles_missing_values() -> None:
    insight = InsightNormalizer.x(
        "x-1",
        {
            "data": {
                "public_metrics": {
                    "impression_count": 100,
                    "like_count": 4,
                    "reply_count": 2,
                    "repost_count": 3,
                },
                "non_public_metrics": {
                    "video_view_count": 70,
                    "video_avg_view_time": 99,
                },
            }
        },
        duration_seconds=30,
        collected_at=NOW,
    )
    assert insight.average_watch_ratio == 1
    assert insight.shares == 3
    assert "video_view_count" in insight.available_metrics

    empty = InsightNormalizer.x(
        "x-2", {}, duration_seconds=30, collected_at=NOW
    )
    assert empty.views == empty.impressions == 0


def test_insight_contract_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        InsightNormalizer.x("x", {}, duration_seconds=0, collected_at=NOW)
    with pytest.raises(ValueError, match="negative"):
        NormalizedInsight(Platform.X, "x", NOW, -1, 0, 0, 0, 0, 0, frozenset())
    with pytest.raises(ValueError, match="watch ratio"):
        NormalizedInsight(Platform.X, "x", NOW, 0, 0, 2, 0, 0, 0, frozenset())


@pytest.mark.parametrize(
    ("method", "remote_id", "expected_path"),
    [
        ("youtube", "yt-1", "youtubeanalytics.googleapis.com/v2/reports"),
        ("instagram", "ig-1", "/ig-1/insights"),
        ("facebook", "fb-1", "/fb-1/video_insights"),
        ("x", "x-1", "/2/tweets/x-1"),
    ],
)
def test_insight_client_builds_platform_requests(
    method: str, remote_id: str, expected_path: str
) -> None:
    transport = FakeTransport(ApiResponse(200, {"data": []}))
    client = PlatformInsightClient(transport)
    if method == "youtube":
        result = client.youtube(
            "yt-1", token="secret", start_date="2026-01-01", end_date="2026-01-02"
        )
    else:
        result = getattr(client, method)(remote_id, token="secret")
    assert result == {"data": []}
    assert expected_path in transport.calls[0]["url"]


def test_insight_client_sanitizes_api_failure() -> None:
    client = PlatformInsightClient(FakeTransport(ApiResponse(403, {"token": "secret"})))
    with pytest.raises(PlatformApiError, match="insight_fetch_failed") as error:
        client.x("1", token="secret")
    assert "secret" not in str(error.value)
