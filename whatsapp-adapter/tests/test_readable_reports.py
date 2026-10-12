from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from truthlens_whatsapp.formatter import format_reports
from truthlens_whatsapp.worker import Worker


def test_formatter_separates_unassessed_links_and_hides_warning_codes(report):
    report["warnings"] = ["llm_provider_error", "search_budget_exhausted"]
    text = "\n".join(format_reports([report]))
    assert "Unassessed retrieved link (not verdict evidence)" in text
    assert "llm_provider_error" not in text and "search_budget_exhausted" not in text
    assert "IST" in text and "T09:00" not in text
    report["claims"][0]["evidence"][0]["stance"] = "neutral"
    assert report["claims"][0]["evidence"][0]["url"] not in "\n".join(format_reports([report]))
    assert report["claims"][0]["evidence"][0]["url"] in "\n".join(
        format_reports([report], sources_only=True)
    )


@pytest.mark.parametrize(
    "command,language", [("HINDI", "hi"), ("MARATHI", "mr"), ("ENGLISH", "en")]
)
async def test_development_language_preferences_without_backend_calls(
    settings, store, message, command, language
):
    message["text"]["body"] = command
    backend, meta = AsyncMock(), AsyncMock()
    store.enqueue([message])
    await Worker(settings, store, meta, backend).process_one()
    assert store.preference(store.identity(message["from"]))["language"] == language
    backend.verify.assert_not_awaited()
    backend.explain.assert_not_awaited()


async def test_original_signed_message_time_forwarded_to_backend(settings, store, message, report):
    settings.response_mode = "backend"
    backend, meta = AsyncMock(), AsyncMock()
    backend.verify.return_value = report
    store.enqueue([message])
    await Worker(settings, store, meta, backend).process_one()
    stamp = backend.verify.call_args.kwargs["message_time"]
    assert int(datetime.fromisoformat(stamp).timestamp()) == int(message["timestamp"])
