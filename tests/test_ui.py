from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from medibot.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    application = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as value:
        yield value


async def test_root_serves_video_studio(client: AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "SELF-LEARNING VIDEO STUDIO" in response.text
    assert 'id="preview-form"' in response.text
    assert 'src="/assets/video.js"' in response.text
    assert 'href="/legacy"' in response.text


async def test_legacy_bot_remains_available(client: AsyncClient) -> None:
    response = await client.get("/legacy")

    assert response.status_code == 200
    assert "MEDIBOT" in response.text
    assert 'id="message-form"' in response.text
    assert 'src="/assets/medibot.js"' in response.text


@pytest.mark.parametrize(
    ("path", "media_types", "expected_text"),
    [
        ("/assets/medibot.css", {"text/css"}, "--teal: #006b60"),
        (
            "/assets/medibot.js",
            {"application/javascript", "text/javascript"},
            'fetch("/v1/messages"',
        ),
    ],
)
async def test_ui_assets_are_served(
    client: AsyncClient,
    path: str,
    media_types: set[str],
    expected_text: str,
) -> None:
    response = await client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].split(";", 1)[0] in media_types
    assert expected_text in response.text
    assert response.headers["cache-control"] == "no-store"


async def test_ui_csp_allows_only_required_same_origin_capabilities(
    client: AsyncClient,
) -> None:
    response = await client.get("/")

    assert response.headers["content-security-policy"] == (
        "default-src 'none'; "
        "connect-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "media-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
