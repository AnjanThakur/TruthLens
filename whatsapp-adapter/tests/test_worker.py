import copy
import time
from unittest.mock import AsyncMock

import pytest
from conftest import extraction

from truthlens_whatsapp.errors import AmbiguousSend, ServiceError
from truthlens_whatsapp.formatter import DEVELOPMENT, format_reports
from truthlens_whatsapp.worker import Worker


@pytest.mark.parametrize("kind", ["text", "url", "image", "audio", "document"])
async def test_five_routes(settings, store, message, report, kind):
    settings.response_mode = "backend"
    backend, meta = AsyncMock(), AsyncMock()
    backend.verify.return_value = report
    if kind == "url":
        message["text"]["body"] = "https://example.test/article"
        backend.extract_url.return_value = extraction("url")
    elif kind != "text":
        message["type"] = kind
        message.pop("text")
        message[kind] = {
            "id": "123456",
            "mime_type": "application/pdf" if kind == "document" else f"{kind}/test",
        }
        meta.media.return_value = (
            b"fixture",
            "application/pdf" if kind == "document" else f"{kind}/test",
        )
        backend.extract.return_value = extraction("pdf" if kind == "document" else kind)
    store.enqueue([message])
    worker = Worker(settings, store, meta, backend)
    assert await worker.process_one()
    store.enqueue([message])
    assert not await worker.process_one()
    assert backend.verify.await_count == 1
    assert backend.verify.call_args.args[1] == ("pdf" if kind == "document" else kind)
    if kind == "url":
        backend.extract_url.assert_awaited_once()
    if kind in {"image", "audio", "document"}:
        backend.extract.assert_awaited_once()
    with store.tx() as db:
        bodies = [
            store.open(row["body"])
            for row in store.execute(db, "SELECT body FROM outbox").fetchall()
        ]
    assert "https://example.test/source" in "\n".join(bodies)


async def test_development_never_calls_backend(settings, store, message):
    meta, backend = AsyncMock(), AsyncMock()
    store.enqueue([message])
    worker = Worker(settings, store, meta, backend)
    await worker.process_one()
    assert not await worker.send_one()
    backend.verify.assert_not_awaited()
    meta.send.assert_not_awaited()
    item = store.next_send()
    assert store.open(item["body"]) == DEVELOPMENT


async def test_provider_failure_has_no_fact_verdict(settings, store, message):
    settings.response_mode = "backend"
    backend, meta = AsyncMock(), AsyncMock()
    backend.verify.side_effect = ServiceError("backend_unavailable")
    store.enqueue([message])
    await Worker(settings, store, meta, backend).process_one()
    body = store.open(store.next_send()["body"])
    assert "No factual verdict" in body and "Unconfirmed" not in body


async def test_stop_suppresses_queued_result_and_window(settings, store, message, report):
    settings.response_mode = "backend"
    settings.meta_outbound_enabled = True
    backend, meta = AsyncMock(), AsyncMock()
    backend.verify.return_value = report
    worker = Worker(settings, store, meta, backend)
    store.enqueue([message])
    await worker.process_one()
    stop = {**message, "id": "wamid.stop", "text": {"body": "STOP"}}
    store.enqueue([stop])
    await worker.send_one()
    meta.send.assert_not_awaited()
    old = {
        **message,
        "id": "wamid.old",
        "from": "15550000002",
        "timestamp": str(int(time.time()) - 86500),
    }
    store.enqueue([old])
    await worker.process_one()  # STOP acknowledgement
    await worker.process_one()  # expired input
    assert backend.verify.await_count == 1


async def test_ambiguous_send_not_retried(settings, store, message):
    settings.meta_outbound_enabled = True
    meta = AsyncMock()
    meta.send.side_effect = AmbiguousSend("send_uncertain")
    store.enqueue([message])
    worker = Worker(settings, store, meta, AsyncMock())
    await worker.process_one()
    assert await worker.send_one()
    assert not await worker.send_one()
    meta.send.assert_awaited_once()


@pytest.mark.parametrize("language", ["hi", "mr"])
async def test_languages_preserve_report(settings, store, message, report, language):
    settings.response_mode = "backend"
    meta, backend = AsyncMock(), AsyncMock()
    backend.verify.return_value = report
    store.enqueue([message])
    worker = Worker(settings, store, meta, backend)
    await worker.process_one()
    changed = copy.deepcopy(report)
    changed["response_language"] = language
    backend.explain.return_value = changed
    command = {
        **message,
        "id": f"wamid.{language}",
        "text": {"body": "HINDI" if language == "hi" else "MARATHI"},
    }
    store.enqueue([command])
    await worker.process_one()
    saved = store.last_report(store.identity(message["from"]))
    assert saved["reports"][0]["claims"] == report["claims"]


@pytest.mark.parametrize(
    "verdict",
    ["verified", "false", "partially_true", "outdated", "misleading_context", "unconfirmed"],
)
def test_all_verdicts_and_message_limits(report, verdict):
    report["claims"][0]["verdict"] = verdict
    report["status"] = "partial"
    report["claims"][0]["explanation"] = "Offline explanation. " * 1000
    parts = format_reports([report])
    assert all(len(part.encode("utf-16-le")) // 2 <= 3500 for part in parts)
    assert "PARTIAL CHECK" in parts[0]
    assert "https://example.test/source" in "\n".join(parts)


async def test_pdf_preview_no_partial_document_claim(settings, store, message):
    settings.response_mode = "backend"
    message.update(type="document", document={"id": "123456", "mime_type": "application/pdf"})
    backend, meta = AsyncMock(), AsyncMock()
    meta.media.return_value = (b"%PDF-test", "application/pdf")
    backend.extract.return_value = extraction("pdf", text_is_preview=True)
    store.enqueue([message])
    await Worker(settings, store, meta, backend).process_one()
    backend.verify.assert_not_awaited()
    assert "No whole-document verdict" in store.open(store.next_send()["body"])
