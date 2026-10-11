import copy
import json

import httpx
import pytest
from conftest import ROOT, extraction

from truthlens_whatsapp.contracts import SCHEMA, validate
from truthlens_whatsapp.errors import AmbiguousSend, ServiceError
from truthlens_whatsapp.meta_client import MetaClient
from truthlens_whatsapp.truthlens_client import TruthLensClient


def test_schema_pin_and_drift(report):
    assert SCHEMA == json.loads(
        (ROOT / "docs/backend-openapi.json").read_text(encoding="utf-8-sig")
    )
    validate(report, "VerificationResult")
    report["claims"][0]["verdict"] = "fake"
    with pytest.raises(ServiceError, match="backend_contract"):
        validate(report, "VerificationResult")


async def test_exact_backend_requests_and_explain_invariants(settings, report):
    settings.backend_enabled = settings.provider_credentials_rotated = True
    calls = []

    def transport(request):
        calls.append(request)
        body = (
            json.loads(request.content)
            if "application/json" in request.headers.get("content-type", "")
            else None
        )
        if request.url.path == "/api/extract":
            assert b'name="file"' in request.content and b"private-media" in request.content
            return httpx.Response(200, json=extraction())
        if request.url.path == "/api/extract/url":
            assert body == {"url": "https://example.test/article"}
            return httpx.Response(200, json=extraction("url"))
        if request.url.path == "/api/explain":
            assert set(body) == {"result", "language", "audience"}
            changed = copy.deepcopy(report)
            changed["response_language"] = "hi"
            changed["claims"][0]["verdict"] = "false"
            return httpx.Response(200, json=changed)
        assert set(body) == {
            "text",
            "input_type",
            "input_language",
            "response_language",
            "audience",
            "jurisdiction",
        }
        return httpx.Response(200, json=report)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        backend = TruthLensClient(settings, http)
        await backend.verify("A fictional test claim.", "text", "en")
        await backend.extract(b"private-media", "image/png")
        await backend.extract_url("https://example.test/article")
        with pytest.raises(ServiceError, match="backend_contract"):
            await backend.explain(report, "hi")
    assert len(calls) == 4


async def test_test_only_revocation_waiver_and_disabled_backend(settings, report):
    settings.provider_key_revocation_waived = True
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(200, json=report)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        backend = TruthLensClient(settings, http)
        with pytest.raises(ServiceError, match="backend_disabled"):
            await backend.verify("A fictional test claim.", "text", "en")
        assert not calls
        settings.backend_enabled = True
        await backend.verify("A fictional test claim.", "text", "en")
        assert len(calls) == 1
        settings.bot_env = "production"
        with pytest.raises(ServiceError, match="backend_disabled"):
            await backend.verify("A fictional test claim.", "text", "en")
        assert len(calls) == 1


@pytest.mark.parametrize("status", [429, 503, 504])
async def test_backend_failures_no_automatic_retry(settings, status):
    settings.backend_enabled = settings.provider_credentials_rotated = True
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(status, text="private provider body", headers={"Retry-After": "60"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        with pytest.raises(ServiceError) as error:
            await TruthLensClient(settings, http).verify("A fictional test claim.", "text", "en")
    assert len(calls) == 1 and str(error.value) == "backend_unavailable"
    assert error.value.retry_after == 60


@pytest.mark.parametrize(
    "kind,mime,data",
    [
        ("image", "image/png", b"\x89PNG\r\n\x1a\nfixture"),
        ("audio", "audio/ogg", b"OggSfixture"),
        ("document", "application/pdf", b"%PDF-fixture"),
    ],
)
async def test_authenticated_media(settings, kind, mime, data):
    settings.meta_outbound_enabled = True
    requests = []

    def transport(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer offline-access-token"
        if request.url.host == "graph.facebook.com":
            return httpx.Response(
                200,
                json={
                    "url": "https://lookaside.fbsbx.com/media",
                    "mime_type": mime,
                    "file_size": len(data),
                },
            )
        return httpx.Response(200, content=data, headers={"content-type": mime})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport), follow_redirects=False
    ) as http:
        assert await MetaClient(settings, http).media("123456", kind) == (data, mime)
    assert len(requests) == 2


@pytest.mark.parametrize("mode", ["host", "size", "signature", "checksum", "redirect"])
async def test_media_security(settings, mode):
    settings.meta_outbound_enabled = True
    data = b"\x89PNG\r\n\x1a\nfixture" if mode != "signature" else b"<html>evil</html>"

    def transport(request):
        if request.url.host == "graph.facebook.com":
            result = {
                "url": "https://lookaside.fbsbx.com/media",
                "mime_type": "image/png",
                "file_size": len(data),
            }
            if mode == "host":
                result["url"] = "https://attacker.test/steal"
            if mode == "size":
                result["file_size"] = settings.max_media_bytes + 1
            if mode == "checksum":
                result["sha256"] = "wrong"
            return httpx.Response(200, json=result)
        return (
            httpx.Response(302, headers={"location": "https://attacker.test"})
            if mode == "redirect"
            else httpx.Response(200, content=data, headers={"content-type": "image/png"})
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport), follow_redirects=False
    ) as http:
        with pytest.raises(ServiceError):
            await MetaClient(settings, http).media("123456", "image")


async def test_approval_gates_and_uncertain_send(settings):
    def transport(request):
        raise AssertionError("No network when disabled")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        with pytest.raises(ServiceError, match="meta_disabled"):
            await MetaClient(settings, http).send("15550000001", "hello", "opaque")
        with pytest.raises(ServiceError, match="backend_disabled"):
            await TruthLensClient(settings, http).verify("A fictional claim", "text", "en")
    settings.meta_outbound_enabled = True
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    ) as http:
        with pytest.raises(AmbiguousSend):
            await MetaClient(settings, http).send("15550000001", "hello", "opaque")
