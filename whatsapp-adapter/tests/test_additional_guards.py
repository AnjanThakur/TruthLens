import copy
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from conftest import ROOT
from pydantic import ValidationError

from truthlens_whatsapp.config import Settings
from truthlens_whatsapp.contracts import validate
from truthlens_whatsapp.errors import ServiceError
from truthlens_whatsapp.meta_client import MetaClient
from truthlens_whatsapp.worker import Worker


def test_website_fixture_matches_exact_person1_schema():
    report = json.loads(
        (ROOT / "frontend/tests/fixtures/person1-response.json").read_text(encoding="utf-8")
    )
    validate(report, "VerificationResult")


def test_backend_configuration_requires_rotation_and_approval(settings):
    args = settings.model_dump()
    args["response_mode"] = "backend"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **args)
    args["backend_enabled"] = args["provider_credentials_rotated"] = True
    assert Settings(_env_file=None, **args).response_mode == "backend"
    args["bot_env"] = "production"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **args)


def test_stop_still_honored_when_queue_full(settings, store, message):
    settings.max_queue_jobs = 1
    store.enqueue([message])
    store.enqueue([{**message, "id": "wamid.stop-full", "text": {"body": "STOP"}}])
    assert store.preference(store.identity(message["from"]))["stopped"] == 1


async def test_rate_limit_retries_bounded(settings, store, message):
    settings.meta_outbound_enabled = True
    meta = AsyncMock()
    meta.send.side_effect = ServiceError("meta_rate_limit", retry_after=60)
    store.enqueue([message])
    worker = Worker(settings, store, meta, AsyncMock())
    await worker.process_one()
    for _ in range(4):
        with store.tx() as db:
            store.execute(db, "UPDATE outbox SET due=0")
        await worker.send_one()
    assert meta.send.await_count == 3
    with store.tx() as db:
        assert store.execute(db, "SELECT state FROM outbox").fetchone()["state"] == "failed"


async def test_stream_size_limit_and_redirect_send(settings):
    settings.meta_outbound_enabled = True
    settings.max_media_bytes = 1024

    def transport(request):
        if request.url.host == "graph.facebook.com":
            return httpx.Response(
                200,
                json={
                    "url": "https://lookaside.fbsbx.com/media",
                    "mime_type": "image/png",
                    "file_size": 1,
                },
            )
        return httpx.Response(
            200, content=b"\x89PNG\r\n\x1a\n" + b"x" * 2000, headers={"content-type": "image/png"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        with pytest.raises(ServiceError, match="media_too_large"):
            await MetaClient(settings, http).media("12345", "image")


async def test_unreadable_media_does_not_verify_and_no_evidence_is_honest(
    settings, store, message, report
):
    settings.response_mode = "backend"
    backend, meta = AsyncMock(), AsyncMock()
    message.update(type="image", image={"id": "12345"})
    meta.media.side_effect = ServiceError("media_unavailable")
    store.enqueue([message])
    await Worker(settings, store, meta, backend).process_one()
    backend.verify.assert_not_awaited()
    from truthlens_whatsapp.formatter import format_reports

    report = copy.deepcopy(report)
    report["claims"][0]["evidence"] = []
    assert "absence of evidence does not establish falsity" in "\n".join(format_reports([report]))


def test_qr_refuses_unverified_number(monkeypatch):
    from truthlens_whatsapp.make_qr import main

    monkeypatch.setattr("sys.argv", ["make_qr", "--number", "15550000001"])
    with pytest.raises(SystemExit):
        main()


async def test_logs_do_not_contain_exception_content(settings, store, message, caplog):
    import logging

    settings.response_mode = "backend"
    backend = AsyncMock()
    backend.verify.side_effect = RuntimeError("private-token-and-message-15550000001")
    store.enqueue([message])
    with caplog.at_level(logging.INFO, logger="truthlens.whatsapp"):
        await Worker(settings, store, AsyncMock(), backend).process_one()
    assert "private-token" not in caplog.text
    assert "15550000001" not in caplog.text
    assert "internal_error" in caplog.text


def test_failed_delivery_after_sent_is_recorded(store, message):
    store.enqueue([message])
    job = store.claim()
    store.prepare(job["id"], ["Reply"])
    item = store.next_send()
    store.send_state(item["id"], "accepted", "wamid.failed")
    store.delivery({"id": "wamid.failed", "status": "sent"})
    store.delivery({"id": "wamid.failed", "status": "failed"})
    with store.tx() as db:
        assert store.execute(db, "SELECT state FROM outbox").fetchone()["state"] == "failed"
