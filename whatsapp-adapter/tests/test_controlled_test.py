import copy
from uuid import uuid4

import httpx
import pytest

from truthlens_whatsapp.controlled_test import RequestBudget, run_selected
from truthlens_whatsapp.errors import ServiceError
from truthlens_whatsapp.truthlens_client import TruthLensClient


async def test_selected_job_does_not_process_or_send_other_queue_entries(settings, store, message):
    settings.meta_outbound_enabled = True
    other = {**message, "id": "wamid.unrelated", "from": "15550000002"}
    store.enqueue([other, message])
    old_job = store.claim(store.identity(other["id"]))
    store.prepare(old_job["id"], ["Unrelated pending reply"])
    store.finish(old_job["id"])
    sent = []

    def remote(request):
        sent.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.sent"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        result = await run_selected(settings, store, http, message["id"], wait_seconds=1)
        again = await run_selected(settings, store, http, message["id"], wait_seconds=1)
    assert result["processed"] and result["backend_requests"] == 0
    assert result["outbox_steps"] == 1
    assert again["outcome"] == "not_new"
    assert len(sent) == 1
    assert "DEVELOPMENT TEST" in sent[0].content.decode()
    with store.tx() as db:
        row = store.execute(
            db, "SELECT state FROM outbox WHERE job_id=?", (old_job["id"],)
        ).fetchone()
    assert row["state"] == "prepared"


async def test_zero_backend_budget_blocks_before_network(settings, store, message):
    settings.meta_outbound_enabled = True
    settings.response_mode = "backend"
    settings.backend_enabled = settings.provider_credentials_rotated = True
    store.enqueue([message])
    calls = []

    def remote(request):
        calls.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.sent"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        result = await run_selected(settings, store, http, message["id"], wait_seconds=1)
    assert result["backend_requests"] == 0
    assert len(calls) == 1 and calls[0].url.host == "graph.facebook.com"
    assert "No factual verdict" in calls[0].content.decode()


async def test_budget_counts_failed_requests_and_refuses_second(settings):
    settings.backend_enabled = settings.provider_credentials_rotated = True
    budget = RequestBudget(1)
    calls = []

    def remote(request):
        calls.append(request)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        backend = TruthLensClient(settings, http, request_budget=budget)
        with pytest.raises(ServiceError, match="backend_unavailable"):
            await backend.extract_url("https://example.test/article")
        with pytest.raises(ServiceError, match="test_budget_exhausted"):
            await backend.extract_url("https://example.test/article")
    assert budget.used == len(calls) == 1


async def test_disabled_flags_and_invalid_selection_make_no_network_calls(settings, store):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: pytest.fail("No network expected"))
    ) as http:
        with pytest.raises(ValueError, match="separately approved"):
            await run_selected(settings, store, http, "wamid.test")
        settings.meta_outbound_enabled = True
        with pytest.raises(ValueError, match="message ID"):
            await run_selected(settings, store, http, "arbitrary text")


async def test_missing_message_stops_without_claiming_other_job(settings, store, message):
    settings.meta_outbound_enabled = True
    store.enqueue([message])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: pytest.fail("No network expected"))
    ) as http:
        result = await run_selected(settings, store, http, "wamid.not-received", wait_seconds=1)
    assert result["outcome"] == "not_received"
    assert store.claim()["id"] == store.identity(message["id"])


async def test_reply_attempt_cap_leaves_remaining_parts_unsent(settings, store, message, report):
    settings.response_mode = "backend"
    settings.backend_enabled = settings.provider_credentials_rotated = True
    settings.meta_outbound_enabled = True
    report["claims"][0]["explanation"] = "Offline fixture explanation. " * 80
    report["summary"] = "Offline fixture summary. " * 200
    # The concise formatter no longer repeats a long overall summary. Exercise
    # the send cap with a genuinely multi-claim report, keeping the assertions.
    original = report["claims"][0]
    report["claims"] = [dict(copy.deepcopy(original), claim_id=str(uuid4())) for _ in range(5)]
    store.enqueue([message])
    calls = []

    def remote(request):
        calls.append(request)
        if request.url.path == "/api/verify":
            return httpx.Response(200, json=report)
        return httpx.Response(200, json={"messages": [{"id": "wamid.sent"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        result = await run_selected(
            settings,
            store,
            http,
            message["id"],
            backend_requests=1,
            send_attempts=1,
            wait_seconds=1,
        )
    assert result["backend_requests"] == result["outbox_steps"] == 1
    assert result["job_state"] == "completed" and result["pending_parts"] > 0
    assert len(calls) == 2
