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


async def test_root_serves_medibot_interface(client: AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "MEDIBOT" in response.text
    assert 'id="message-form"' in response.text
    assert 'src="/assets/medibot.js"' in response.text
    assert "No diagnosis" in response.text


@pytest.mark.parametrize(
    ("path", "media_type", "expected_text"),
    [
        ("/assets/medibot.css", "text/css", "--teal: #006b60"),
        ("/assets/medibot.js", "application/javascript", 'fetch("/v1/messages"'),
    ],
)
async def test_ui_assets_are_served(
    client: AsyncClient,
    path: str,
    media_type: str,
    expected_text: str,
) -> None:
    response = await client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
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
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
