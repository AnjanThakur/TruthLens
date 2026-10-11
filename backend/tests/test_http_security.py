import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from app.errors import AppError
from app.main import create_app
from app.services.extract.url import SafeFetcher, canonical_url, is_public_ip
from app.services.search.ledger import identity


class Resolver:
    def __init__(self, addresses):
        self.addresses = addresses
        self.calls = []

    async def resolve(self, host, port):
        self.calls.append(host)
        return self.addresses.get(host, ["93.184.216.34"])


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "192.168.0.1",
        "::1",
        "::ffff:127.0.0.1",
        "224.0.0.1",
        "100.64.0.1",
        "192.0.2.1",
    ],
)
def test_non_public_ips(address):
    assert not is_public_ip(address)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://site.com",
        "https://u:p@site.com",
        "https://site.com:8080",
        "https://site.com\\@127.0.0.1",
        "https://site.com\n/path",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(AppError, match="public HTTP"):
        canonical_url(url)


async def test_private_redirect_blocked_and_public_connection_pinned(settings):
    seen = []

    async def handler(request):
        seen.append(request)
        return httpx.Response(302, headers={"location": "http://internal.test/secret"})

    resolver = Resolver({"internal.test": ["127.0.0.1"]})
    fetcher = SafeFetcher(settings, resolver, httpx.MockTransport(handler))
    with pytest.raises(AppError) as error:
        await fetcher.fetch("https://public.test/article")
    assert error.value.code == "unsafe_url"
    assert len(seen) == 1
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "public.test"
    assert seen[0].extensions["sni_hostname"] == "public.test"


async def test_mixed_dns_answers_blocked(settings):
    resolver = Resolver({"mixed.test": ["93.184.216.34", "10.0.0.1"]})
    fetcher = SafeFetcher(
        settings, resolver, httpx.MockTransport(lambda r: pytest.fail("Must not connect"))
    )
    with pytest.raises(AppError):
        await fetcher.fetch("https://mixed.test")


async def test_stream_limit_and_redirect_limit(settings):
    settings.max_url_bytes = 1024
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, headers={"content-type": "text/html"}, content=b"a" * 1025)
    )
    with pytest.raises(AppError) as error:
        await SafeFetcher(settings, Resolver({}), transport).fetch("https://public.test")
    assert error.value.code == "url_too_large"
    transport = httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "/again"}))
    with pytest.raises(AppError) as error:
        await SafeFetcher(settings, Resolver({}), transport).fetch("https://public.test")
    assert error.value.code == "url_redirect_limit"


def test_authority_registry_avoids_suffix_and_official_looking_trust():
    assert identity("https://rbi.org.in/a")[1] == "primary"
    assert identity("https://rbi.org.in.evil.test/a")[1] == "other"
    assert identity("https://new-not-reviewed.gov.in/a")[1] == "other"


def test_boot_health_and_keyless_verify(settings):
    client = TestClient(create_app(settings))
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["capabilities"]["llm"] is False
    response = client.post("/api/verify", json={"text": "All notes are invalid."})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_unavailable"
    assert response.headers["x-request-id"] == response.json()["error"]["request_id"]


def test_validation_errors_dont_echo_content_and_logs_private(client, caplog):
    private = "PERSONAL_OTP_123456"
    with caplog.at_level(logging.INFO, logger="truthlens.requests"):
        response = client.post("/api/verify", json={"text": private, "response_language": "xx"})
    assert response.status_code == 422
    assert private not in response.text and private not in caplog.text
    assert "request_id" in caplog.text
    assert client.post("/api/verify", json={"text": " "}).status_code == 422
    assert client.get("/unknown").json()["error"]["code"] == "http_error"


def test_actual_body_limit_and_cors(settings):
    client = TestClient(create_app(settings))
    response = client.post("/api/verify", content=b"x" * (256 * 1024 + 1))
    assert response.status_code == 413
    allowed = client.options(
        "/api/verify",
        headers={"origin": "http://localhost:3000", "access-control-request-method": "POST"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    denied = client.options(
        "/api/verify",
        headers={"origin": "https://evil.test", "access-control-request-method": "POST"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_request_deadline(settings):
    import asyncio

    settings.request_timeout_seconds = 0.01  # Deliberately below validated deployment minimum.
    app = create_app(settings)

    @app.get("/slow")
    async def slow():
        await asyncio.sleep(1)

    response = TestClient(app).get("/slow")
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "request_timeout"
