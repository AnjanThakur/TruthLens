import base64
import hashlib
import hmac
import time
from datetime import UTC, datetime
from email.utils import format_datetime
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlencode

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import ValidationError

from truthlens_whatsapp.config import Settings
from truthlens_whatsapp.configure_twilio import update_token, write_config
from truthlens_whatsapp.errors import AmbiguousSend, ServiceError
from truthlens_whatsapp.formatter import DEVELOPMENT
from truthlens_whatsapp.main import create_app
from truthlens_whatsapp.store import Store
from truthlens_whatsapp.twilio_client import TwilioClient, split_reply
from truthlens_whatsapp.worker import Worker

ACCOUNT = "AC" + "a" * 32
SID = "SM" + "b" * 32
OUTBOUND = "SM" + "c" * 32
PATH = "/webhook/twilio/whatsapp"


@pytest.fixture
def twilio_settings(tmp_path):
    return Settings(
        _env_file=None,
        messaging_provider="twilio",
        twilio_account_sid=ACCOUNT,
        twilio_auth_token="offline-twilio-auth-token",
        twilio_whatsapp_number="whatsapp:+15550000000",
        twilio_public_base_url="https://offline.example.test",
        state_encryption_key=Fernet.generate_key().decode(),
        identity_hash_secret="offline-hashing-secret-" * 3,
        database_url=f"sqlite:///{tmp_path / 'twilio.sqlite3'}",
    )


@pytest.fixture
def inbound():
    return {
        "AccountSid": ACCOUNT,
        "MessageSid": SID,
        "From": "whatsapp:+15550000001",
        "To": "whatsapp:+15550000000",
        "Body": "Hi",
        "NumMedia": "0",
        "FutureTwilioField": "included in the signature",
    }


def signed(settings, form, path=PATH):
    # Independent implementation of the documented algorithm, not SDK self-comparison.
    source = settings.twilio_public_base_url + path
    source += "".join(key + form[key] for key in sorted(form))
    signature = base64.b64encode(
        hmac.new(
            settings.twilio_auth_token.get_secret_value().encode(), source.encode(), hashlib.sha1
        ).digest()
    ).decode()
    return {"X-Twilio-Signature": signature, "Content-Type": "application/x-www-form-urlencoded"}


def receipt(settings, *, age=0, **overrides):
    return {
        "sid": SID,
        "account_sid": settings.twilio_account_sid,
        "from": "whatsapp:+15550000001",
        "to": settings.twilio_whatsapp_number,
        "status": "received",
        "date_created": format_datetime(datetime.fromtimestamp(time.time() - age, UTC)),
        **overrides,
    }


async def test_signed_webhook_worker_reply_and_delivery(twilio_settings, inbound):
    settings = twilio_settings
    settings.twilio_outbound_enabled = True
    store, sends = Store(settings), []

    def remote(request):
        assert request.url.host == "api.twilio.com"
        assert request.headers["authorization"].startswith("Basic ")
        if request.method == "GET":
            assert request.url.path.endswith(f"/Messages/{SID}.json")
            return httpx.Response(200, json=receipt(settings))
        sends.append(parse_qs(request.content.decode()))
        return httpx.Response(201, json={"sid": OUTBOUND})

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        with TestClient(create_app(settings, store)) as client:
            headers = signed(settings, inbound)
            for _ in range(2):
                response = client.post(PATH, content=urlencode(inbound), headers=headers)
                assert response.status_code == 200 and response.text == "<Response/>"
            backend = AsyncMock()
            worker = Worker(settings, store, TwilioClient(settings, http), backend)
            assert await worker.process_one()
            assert not await worker.process_one()
            assert await worker.send_one()
            assert not await worker.send_one()
            assert len(sends) == 1 and sends[0]["Body"] == [DEVELOPMENT]
            backend.verify.assert_not_awaited()
            callback = sends[0]["StatusCallback"][0].removeprefix(settings.twilio_public_base_url)
            status = {"AccountSid": ACCOUNT, "MessageSid": OUTBOUND, "MessageStatus": "delivered"}
            assert (
                client.post(
                    callback, content=urlencode(status), headers=signed(settings, status, callback)
                ).status_code
                == 204
            )
            with store.tx() as db:
                assert (
                    store.execute(db, "SELECT state FROM outbox").fetchone()["state"] == "delivered"
                )
            assert client.post("/webhook/whatsapp", json={}).status_code == 404
            assert "offline-twilio-auth-token" not in client.get("/health").text


@pytest.mark.parametrize("mode", ["twiml", "empty"])
def test_webhook_ack_modes_preserve_signature_and_durable_deduplication(
    twilio_settings, inbound, mode
):
    twilio_settings.twilio_webhook_ack_mode = mode
    store = Store(twilio_settings)
    with TestClient(create_app(twilio_settings, store)) as client:
        bad_headers = signed(twilio_settings, inbound)
        bad_headers["X-Twilio-Signature"] = "invalid"
        assert client.post(PATH, content=urlencode(inbound), headers=bad_headers).status_code == 403
        assert store.claim() is None
        for _ in range(2):
            response = client.post(
                PATH, content=urlencode(inbound), headers=signed(twilio_settings, inbound)
            )
            assert response.status_code == 200
            assert response.text == ("<Response/>" if mode == "twiml" else "")
            assert response.headers["content-type"].startswith(
                "application/xml" if mode == "twiml" else "text/plain"
            )
        with store.tx() as db:
            assert store.execute(db, "SELECT COUNT(*) AS n FROM jobs").fetchone()["n"] == 1
            assert store.execute(db, "SELECT COUNT(*) AS n FROM outbox").fetchone()["n"] == 0


def test_webhook_ack_mode_rejects_unsupported_configuration(twilio_settings):
    with pytest.raises(ValidationError, match="acknowledgement mode"):
        Settings(
            **{**twilio_settings.model_dump(), "twilio_webhook_ack_mode": "arbitrary"},
            _env_file=None,
        )


@pytest.mark.parametrize(
    "change", ["signature", "body", "account", "recipient", "media_host", "query"]
)
def test_rejects_invalid_requests(twilio_settings, inbound, change):
    store = Store(twilio_settings)
    path, form = PATH, dict(inbound)
    if change == "account":
        form["AccountSid"] = "AC" + "d" * 32
    elif change == "recipient":
        form["To"] = "whatsapp:+15550000002"
    elif change == "media_host":
        form.update(
            NumMedia="1",
            MediaContentType0="image/png",
            MediaUrl0="https://attacker.invalid/private",
        )
    headers = signed(twilio_settings, form)
    if change == "signature":
        headers["X-Twilio-Signature"] = "wrong"
    elif change == "body":
        form["Body"] = "tampered"
    elif change == "query":
        path += "?unexpected=true"
    with TestClient(create_app(twilio_settings, store)) as client:
        assert client.post(path, content=urlencode(form), headers=headers).status_code in {400, 403}
    assert store.claim() is None


def test_disabled_transport_and_body_limits(settings, store, twilio_settings, inbound):
    with TestClient(create_app(settings, store)) as client:
        assert (
            client.post(
                PATH, content=urlencode(inbound), headers=signed(twilio_settings, inbound)
            ).status_code
            == 404
        )
    with TestClient(create_app(twilio_settings, Store(twilio_settings))) as client:
        assert client.post(PATH, json=inbound).status_code == 415
        assert (
            client.post(
                PATH,
                content=b"x" * (twilio_settings.max_webhook_bytes + 1),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ).status_code
            == 413
        )


async def test_sending_disabled_leaves_queue_and_makes_no_requests(twilio_settings, inbound):
    store = Store(twilio_settings)
    with TestClient(create_app(twilio_settings, store)) as client:
        assert (
            client.post(
                PATH, content=urlencode(inbound), headers=signed(twilio_settings, inbound)
            ).status_code
            == 200
        )
    remote, backend = AsyncMock(), AsyncMock()
    worker = Worker(twilio_settings, store, remote, backend)
    assert not await worker.process_one() and not await worker.send_one()
    remote.received_at.assert_not_awaited()
    remote.send.assert_not_awaited()
    assert store.claim() is not None


@pytest.mark.parametrize(
    "overrides", [{"age": 86500}, {"from": "whatsapp:+15550000099"}, {"status": "sent"}]
)
async def test_receipt_verification_prevents_paid_calls_and_replies(
    twilio_settings, inbound, overrides
):
    settings = twilio_settings
    settings.twilio_outbound_enabled = True
    store = Store(settings)
    with TestClient(create_app(settings, store)) as client:
        client.post(PATH, content=urlencode(inbound), headers=signed(settings, inbound))
    calls = []

    def remote(request):
        calls.append(request.method)
        return httpx.Response(200, json=receipt(settings, **overrides))

    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        backend = AsyncMock()
        worker = Worker(settings, store, TwilioClient(settings, http), backend)
        assert await worker.process_one()
        assert not await worker.send_one()
        backend.verify.assert_not_awaited()
    assert calls == ["GET"]


def test_provider_database_isolation(settings, store, twilio_settings):
    twilio_settings.database_url = settings.database_url
    with pytest.raises(ValueError, match="separate database"):
        Store(twilio_settings)


def test_content_expires_but_twilio_replay_tombstone_remains(twilio_settings, inbound):
    store = Store(twilio_settings)
    with TestClient(create_app(twilio_settings, store)) as client:
        headers = signed(twilio_settings, inbound)
        assert client.post(PATH, content=urlencode(inbound), headers=headers).status_code == 200
        with store.tx() as db:
            store.execute(
                db, "UPDATE jobs SET state='completed',created=?", (time.time() - 10 * 86400,)
            )
        store.cleanup()
        with store.tx() as db:
            row = store.execute(db, "SELECT payload,report FROM jobs").fetchone()
            assert row is not None and row["payload"] is None and row["report"] is None
        assert client.post(PATH, content=urlencode(inbound), headers=headers).status_code == 200
        assert store.claim() is None


@pytest.mark.parametrize("kind", ["text", "url", "image", "audio", "document"])
async def test_twilio_routes_use_only_shared_backend(twilio_settings, inbound, report, kind):
    from conftest import extraction

    settings = twilio_settings
    settings.twilio_outbound_enabled = True
    settings.backend_enabled = settings.provider_credentials_rotated = True
    settings.response_mode = "backend"
    form = dict(inbound)
    media = {
        "image": ("image/png", b"\x89PNG\r\n\x1a\nfixture"),
        "audio": ("audio/ogg", b"OggSfixture"),
        "document": ("application/pdf", b"%PDF-fixture"),
    }
    if kind == "url":
        form["Body"] = "https://example.test/news"
    elif kind in media:
        form.update(
            NumMedia="1",
            MediaContentType0=media[kind][0],
            MediaUrl0=f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT}/Messages/{SID}/Media/ME{'d' * 32}",
        )
    store = Store(settings)
    with TestClient(create_app(settings, store)) as client:
        assert (
            client.post(PATH, content=urlencode(form), headers=signed(settings, form)).status_code
            == 200
        )

    def remote(request):
        if "/Media/" in request.url.path:
            return httpx.Response(
                200, headers={"Content-Type": media[kind][0]}, content=media[kind][1]
            )
        return httpx.Response(200, json=receipt(settings))

    backend = AsyncMock()
    backend.verify.return_value = report
    backend.extract_url.return_value = extraction("url")
    backend.extract.return_value = extraction("pdf" if kind == "document" else kind)
    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        worker = Worker(settings, store, TwilioClient(settings, http), backend)
        assert await worker.process_one()
    backend.verify.assert_awaited_once()
    assert backend.verify.call_args.args[1] == ("pdf" if kind == "document" else kind)
    if kind == "url":
        backend.extract_url.assert_awaited_once()
    elif kind in media:
        backend.extract.assert_awaited_once_with(media[kind][1], media[kind][0])


def test_duplicate_fields_are_rejected(twilio_settings, inbound):
    from starlette.datastructures import FormData
    from twilio.request_validator import RequestValidator

    pairs = [*inbound.items(), ("Body", "ambiguous")]
    signature = RequestValidator(
        twilio_settings.twilio_auth_token.get_secret_value()
    ).compute_signature(twilio_settings.twilio_public_base_url + PATH, FormData(pairs))
    store = Store(twilio_settings)
    with TestClient(create_app(twilio_settings, store)) as client:
        assert (
            client.post(
                PATH,
                content=urlencode(pairs),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": signature,
                },
            ).status_code
            == 400
        )
    assert store.claim() is None


@pytest.mark.parametrize("status", [429, 503, 401])
async def test_send_failures_are_distinct(twilio_settings, status):
    twilio_settings.twilio_outbound_enabled = True
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status))
    ) as http:
        expected = AmbiguousSend if status == 503 else ServiceError
        with pytest.raises(expected) as error:
            await TwilioClient(twilio_settings, http).send(
                "15550000001", DEVELOPMENT, "00000000-0000-0000-0000-000000000001"
            )
        assert (
            error.value.code
            == {429: "twilio_rate_limit", 503: "send_uncertain", 401: "twilio_rejected"}[status]
        )


@pytest.mark.parametrize(
    "kind,mime,data",
    [
        ("image", "image/png", b"\x89PNG\r\n\x1a\nfixture"),
        ("audio", "audio/ogg", b"OggSfixture"),
        ("document", "application/pdf", b"%PDF-fixture"),
    ],
)
async def test_authenticated_bounded_media(twilio_settings, kind, mime, data):
    twilio_settings.twilio_outbound_enabled = True
    path = f"/2010-04-01/Accounts/{ACCOUNT}/Messages/{SID}/Media/ME{'d' * 32}"
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"Content-Type": mime}, content=data)
        )
    ) as http:
        assert await TwilioClient(twilio_settings, http).media(path, kind) == (data, mime)


async def test_media_redirect_does_not_leak_credentials(twilio_settings):
    twilio_settings.twilio_outbound_enabled = True
    calls = []

    def remote(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://attacker.invalid/media"})

    path = f"/2010-04-01/Accounts/{ACCOUNT}/Messages/{SID}/Media/ME{'d' * 32}"
    async with httpx.AsyncClient(transport=httpx.MockTransport(remote)) as http:
        with pytest.raises(ServiceError, match="media_unavailable"):
            await TwilioClient(twilio_settings, http).media(path, "image")
    assert len(calls) == 1 and calls[0].startswith("https://api.twilio.com/")


def test_private_config_preserves_existing_file_and_disables_calls(tmp_path):
    path = tmp_path / ".env.twilio"
    write_config(path, ACCOUNT, "0" * 32, "whatsapp:+15550000000", "https://offline.example.test")
    config = Settings(_env_file=path)
    assert (
        config.messaging_provider == "twilio"
        and not config.outbound_enabled
        and not config.backend_enabled
    )
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        write_config(
            path, ACCOUNT, "1" * 32, "whatsapp:+15550000000", "https://offline.example.test"
        )
    assert path.read_bytes() == original


def test_token_update_preserves_encryption_identity_and_disabled_flags(tmp_path):
    path = tmp_path / ".env.twilio"
    write_config(path, ACCOUNT, "0" * 32, "whatsapp:+15550000000", "https://offline.example.test")
    before = Settings(_env_file=path)
    update_token(path, "a" * 32)
    after = Settings(_env_file=path)
    assert after.twilio_auth_token.get_secret_value() == "a" * 32
    assert before.model_dump(exclude={"twilio_auth_token"}) == after.model_dump(
        exclude={"twilio_auth_token"}
    )
    original = path.read_bytes()
    for invalid in ["", "wrong-value", "•" * 32, "z" * 32, "a" * 31, "a" * 32 + "\n"]:
        with pytest.raises(ValueError):
            update_token(path, invalid)
        assert path.read_bytes() == original


def test_private_wizard_rejects_wrong_token_without_creating_file(tmp_path):
    path = tmp_path / ".env.twilio"
    with pytest.raises(ValueError):
        write_config(
            path,
            ACCOUNT,
            "copied-placeholder",
            "whatsapp:+15550000000",
            "https://offline.example.test",
        )
    assert not path.exists()
    with pytest.raises(ValueError):
        update_token(path, "a" * 32)
    assert not path.exists()


def test_configuration_and_unicode_limits(twilio_settings):
    values = twilio_settings.model_dump()
    for changes in [
        {"bot_env": "production"},
        {"meta_outbound_enabled": True},
        {"twilio_public_base_url": "http://insecure.invalid"},
    ]:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **{**values, **changes})
    text = "A😀" * 2000
    parts = split_reply(text)
    assert "".join(parts) == text
    assert all(len(part.encode("utf-16-le")) // 2 <= 1500 for part in parts)


def test_source_links_are_not_split_or_silently_shortened():
    url = "https://example.test/source?" + "a" * 900
    text = "Offline source information " * 50 + "\n" + url + "\nCheck the original."
    parts = split_reply(text)
    assert "".join(parts) == text
    assert any(url in part for part in parts)
    assert all(len(part.encode("utf-16-le")) // 2 <= 1500 for part in parts)
    oversized = "https://example.test/" + "a" * 1600
    omitted = "".join(split_reply("Source: test publisher\n" + oversized))
    assert oversized not in omitted
    assert "Source URL omitted" in omitted and "test publisher" in omitted
