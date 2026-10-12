import logging
import time
from unittest.mock import AsyncMock
from urllib.parse import parse_qs

import httpx
import pytest

from truthlens_whatsapp.config import Settings
from truthlens_whatsapp.errors import AmbiguousSend, TwilioSendError
from truthlens_whatsapp.formatter import DEVELOPMENT
from truthlens_whatsapp.store import Store
from truthlens_whatsapp.twilio_client import TwilioClient
from truthlens_whatsapp.worker import Worker

CALLBACK = "00000000-0000-0000-0000-000000000001"
OUTBOUND = "SM" + "c" * 32
PRIVATE = "secret-token private-message whatsapp:+15550000001"


@pytest.fixture
def twilio(settings):
    return Settings(
        _env_file=None,
        **{
            **settings.model_dump(),
            "messaging_provider": "twilio",
            "twilio_outbound_enabled": True,
            "twilio_account_sid": "AC" + "a" * 32,
            "twilio_auth_token": "offline-private-auth-token",
            "twilio_whatsapp_number": "whatsapp:+15550000000",
            "twilio_public_base_url": "https://offline.example.test",
        },
    )


@pytest.mark.parametrize("status,code", [(400, 63016), (401, 20003), (403, 21608)])
async def test_rejection_diagnostics_reach_worker_without_private_data(
    twilio, message, caplog, status, code
):
    store = Store(twilio)
    message["id"] = "twilio:SM" + "b" * 32
    store.enqueue([message])
    calls = []

    def remote(request):
        calls.append(request.method)
        return httpx.Response(
            status,
            json={"code": code, "message": PRIVATE, "more_info": PRIVATE},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        transport = TwilioClient(twilio, http)
        transport.received_at = AsyncMock(return_value=int(time.time()))
        backend = AsyncMock()
        worker = Worker(twilio, store, transport, backend)
        with caplog.at_level(logging.INFO, logger="truthlens.whatsapp"):
            assert await worker.process_one()
            assert await worker.send_one()
            assert not await worker.send_one()  # Definite rejection is never retried.
        backend.verify.assert_not_awaited()
        backend.extract.assert_not_awaited()
    assert calls == ["POST"]
    assert f"http_status={status} twilio_error_code={code}" in caplog.text
    assert "outcome=failed" in caplog.text
    for forbidden in [PRIVATE, "15550000001", "15550000000", "offline-private-auth-token"]:
        assert forbidden not in caplog.text
    with store.tx() as db:
        item = store.execute(db, "SELECT state,attempts,meta_id FROM outbox").fetchone()
    assert (item["state"], item["attempts"], item["meta_id"]) == ("failed", 1, None)


@pytest.mark.parametrize(
    "response,expected_code",
    [
        (httpx.Response(400, text=PRIVATE), None),
        (httpx.Response(400, json=[{"code": 63016}]), None),
        (httpx.Response(401, json=None), None),
        (httpx.Response(403, json={"code": PRIVATE}), None),
        (httpx.Response(400, json={"code": True}), None),
        (httpx.Response(400, json={"code": 15550000001}), None),
        (httpx.Response(400, json={"code": {"secret": PRIVATE}}), None),
        (httpx.Response(400, json={"code": 63016, "message": PRIVATE}), 63016),
        (httpx.Response(400, content=b"x" * 65537), None),
    ],
)
async def test_untrusted_error_responses_keep_only_numeric_diagnostics(
    twilio, response, expected_code
):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as http:
        with pytest.raises(TwilioSendError) as error:
            await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, CALLBACK)
    assert str(error.value) == "twilio_rejected"
    assert error.value.http_status == response.status_code
    assert error.value.twilio_error_code == expected_code
    assert PRIVATE not in repr(error.value)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(201, text=PRIVATE),
        httpx.Response(201, json=[]),
        httpx.Response(201, json=None),
        httpx.Response(201, json={}),
        httpx.Response(201, json={"sid": "not-a-message-sid"}),
        httpx.Response(201, json={"sid": 123}),
        httpx.Response(201, content=b"x" * 65537),
        httpx.Response(503, json={"code": 20500, "message": PRIVATE}),
    ],
)
async def test_malformed_success_and_server_errors_remain_uncertain(twilio, response):
    calls = []

    def remote(request):
        calls.append(request)
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        with pytest.raises(AmbiguousSend) as error:
            await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, CALLBACK)
    assert len(calls) == 1
    assert error.value.http_status == response.status_code
    assert error.value.__cause__ is None
    assert PRIVATE not in repr(error.value)


@pytest.mark.parametrize("state", ["failed", "undelivered"])
async def test_success_http_with_explicit_failed_message_is_rejected(twilio, state):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                201, json={"sid": OUTBOUND, "status": state, "error_code": 63015}
            )
        )
    ) as http:
        with pytest.raises(TwilioSendError) as error:
            await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, CALLBACK)
    assert error.value.http_status == 201
    assert error.value.twilio_error_code == 63015
    assert not isinstance(error.value, AmbiguousSend)


async def test_success_preserves_authenticated_request_and_callback(twilio):
    def remote(request):
        assert request.method == "POST" and request.url.host == "api.twilio.com"
        assert request.headers["authorization"].startswith("Basic ")
        assert parse_qs(request.content.decode()) == {
            "From": [twilio.twilio_whatsapp_number],
            "To": ["whatsapp:+15550000001"],
            "Body": [DEVELOPMENT],
            "StatusCallback": [f"{twilio.twilio_public_base_url}/webhook/twilio/status/{CALLBACK}"],
        }
        return httpx.Response(201, json={"sid": OUTBOUND, "status": "queued"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        assert (
            await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, CALLBACK)
            == f"twilio:{OUTBOUND}"
        )


async def test_timeout_diagnostics_never_include_request_or_exception(twilio):
    def remote(request):
        raise httpx.ReadTimeout(PRIVATE, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        with pytest.raises(AmbiguousSend) as error:
            await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, CALLBACK)
    assert error.value.http_status is None and error.value.twilio_error_code is None
    assert error.value.__cause__ is None and str(error.value) == "send_uncertain"


async def test_invalid_callback_rejected_locally_without_network(twilio):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: pytest.fail("No HTTP expected"))
    ) as http:
        with pytest.raises(TwilioSendError) as error:
            await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, PRIVATE)
    assert error.value.http_status is None


async def test_rate_limit_keeps_retry_guidance_and_safe_code(twilio):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                429, json={"code": 20429, "message": PRIVATE}, headers={"Retry-After": "12"}
            )
        )
    ) as http:
        with pytest.raises(TwilioSendError) as error:
            await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, CALLBACK)
    assert error.value.code == "twilio_rate_limit" and error.value.retry_after == 12
    assert error.value.http_status == 429 and error.value.twilio_error_code == 20429


async def test_selected_fresh_twilio_test_preserves_old_failed_outbox(twilio, message):
    from datetime import UTC, datetime
    from email.utils import format_datetime

    from truthlens_whatsapp.controlled_test import run_selected

    store = Store(twilio)
    old = {**message, "id": "twilio:SM" + "d" * 32}
    store.enqueue([old])
    job = store.claim()
    store.prepare(job["id"], ["Old failed reply"])
    store.finish(job["id"])
    item = store.next_send()
    store.send_state(item["id"], "failed")
    with store.tx() as db:
        before = dict(
            store.execute(db, "SELECT * FROM outbox WHERE id=?", (item["id"],)).fetchone()
        )
    fresh_sid = "SM" + "b" * 32
    store.enqueue([{**message, "id": "twilio:" + fresh_sid}])
    calls = []

    def remote(request):
        calls.append(request.method)
        if request.method == "GET":
            assert request.url.path.endswith(f"/Messages/{fresh_sid}.json")
            return httpx.Response(
                200,
                json={
                    "sid": fresh_sid,
                    "account_sid": twilio.twilio_account_sid,
                    "from": "whatsapp:+" + message["from"],
                    "to": twilio.twilio_whatsapp_number,
                    "status": "received",
                    "date_created": format_datetime(datetime.now(UTC)),
                },
            )
        return httpx.Response(400, json={"code": 63016, "message": PRIVATE})

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        result = await run_selected(twilio, store, http, fresh_sid, wait_seconds=1)
        again = await run_selected(twilio, store, http, fresh_sid, wait_seconds=1)
    assert calls == ["GET", "POST"]
    assert result["backend_requests"] == 0 and result["outbox_steps"] == 1
    assert again["outcome"] == "not_new"
    with store.tx() as db:
        after = dict(store.execute(db, "SELECT * FROM outbox WHERE id=?", (item["id"],)).fetchone())
    assert before == after


async def test_trial_content_sid_sends_template_without_body_or_variables(twilio):
    twilio.twilio_development_content_sid = "HX" + "e" * 32
    calls = []

    def remote(request):
        calls.append(request)
        data = parse_qs(request.content.decode())
        assert data == {
            "From": [twilio.twilio_whatsapp_number],
            "To": ["whatsapp:+15550000001"],
            "ContentSid": [twilio.twilio_development_content_sid],
            "StatusCallback": [f"{twilio.twilio_public_base_url}/webhook/twilio/status/{CALLBACK}"],
        }
        return httpx.Response(201, json={"sid": OUTBOUND, "status": "queued"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        assert await TwilioClient(twilio, http).send("15550000001", DEVELOPMENT, CALLBACK)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "changes,body",
    [
        ({"response_mode": "backend"}, DEVELOPMENT),
        ({"backend_enabled": True}, DEVELOPMENT),
        ({"bot_env": "production"}, DEVELOPMENT),
        ({"twilio_development_content_sid": "invalid"}, DEVELOPMENT),
        ({}, "TruthLens: stopped."),
        ({}, "A factual result with sources."),
        ({}, "No factual verdict was generated."),
    ],
)
async def test_trial_template_never_replaces_fact_or_command_replies(twilio, changes, body):
    twilio.twilio_development_content_sid = "HX" + "e" * 32
    for key, value in changes.items():
        setattr(twilio, key, value)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: pytest.fail("No HTTP expected"))
    ) as http:
        with pytest.raises(TwilioSendError, match="twilio_template_only"):
            await TwilioClient(twilio, http).send("15550000001", body, CALLBACK)


@pytest.mark.parametrize(
    "changes",
    [
        {"twilio_development_content_sid": "SM" + "e" * 32},
        {"twilio_development_content_sid": "HX" + "e" * 31},
        {"backend_enabled": True},
        {"response_mode": "backend", "backend_enabled": True, "provider_credentials_rotated": True},
    ],
)
def test_template_configuration_fails_closed(twilio, changes):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **{
                **twilio.model_dump(),
                "twilio_development_content_sid": "HX" + "e" * 32,
                **changes,
            },
        )


def test_template_configuration_preserves_private_state(twilio):
    values = twilio.model_dump()
    configured = Settings(
        _env_file=None, **{**values, "twilio_development_content_sid": "HX" + "e" * 32}
    )
    assert configured.model_dump(exclude={"twilio_development_content_sid"}) == twilio.model_dump(
        exclude={"twilio_development_content_sid"}
    )
