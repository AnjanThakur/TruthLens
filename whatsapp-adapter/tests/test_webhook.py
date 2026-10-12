import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from truthlens_whatsapp.main import create_app


def signed(settings, event):
    raw = json.dumps(event).encode()
    signature = hmac.new(
        settings.meta_app_secret.get_secret_value().encode(), raw, hashlib.sha256
    ).hexdigest()
    return raw, {"X-Hub-Signature-256": f"sha256={signature}"}


def test_challenge(settings, store):
    with TestClient(create_app(settings, store)) as client:
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "offline-verify-token",
            "hub.challenge": "123456",
        }
        response = client.get("/webhook/whatsapp", params=params)
        assert response.status_code == 200 and response.text == "123456"
        assert response.headers["cache-control"] == "no-store"
        params["hub.verify_token"] = "wrong"
        assert client.get("/webhook/whatsapp", params=params).status_code == 403


def test_raw_signature_dedup_and_wrong_account(settings, store, event):
    raw, headers = signed(settings, event)
    with TestClient(create_app(settings, store)) as client:
        assert (
            client.post("/webhook/whatsapp", content=raw + b" ", headers=headers).status_code == 403
        )
        assert store.claim() is None
        assert client.post("/webhook/whatsapp", content=raw, headers=headers).status_code == 200
        assert client.post("/webhook/whatsapp", content=raw, headers=headers).status_code == 200
        assert store.claim() is not None
        assert store.claim() is None
        event["entry"][0]["id"] = "wrong"
        raw, headers = signed(settings, event)
        assert client.post("/webhook/whatsapp", content=raw, headers=headers).status_code == 200


def test_status_only_health_and_limits(settings, store, event):
    value = event["entry"][0]["changes"][0]["value"]
    value.pop("messages")
    value["statuses"] = [{"id": "unknown", "status": "delivered"}]
    with TestClient(create_app(settings, store)) as client:
        raw, headers = signed(settings, event)
        assert client.post("/webhook/whatsapp", content=raw, headers=headers).status_code == 200
        assert store.claim() is None
        assert (
            client.post(
                "/webhook/whatsapp", content=b"x" * (settings.max_webhook_bytes + 1)
            ).status_code
            == 413
        )
        assert client.get("/health").json()["response_mode"] == "development"
        assert "offline-app-secret" not in client.get("/health").text


@pytest.mark.parametrize("mutation", ["sender", "timestamp", "body"])
def test_malformed_and_atomic_batch(settings, store, event, mutation):
    import copy

    messages = event["entry"][0]["changes"][0]["value"]["messages"]
    bad = copy.deepcopy(messages[0])
    bad["id"] = "wamid.bad"
    if mutation == "sender":
        bad["from"] = "not-a-phone"
    elif mutation == "timestamp":
        bad["timestamp"] = "invalid"
    else:
        bad["text"]["body"] = 5
    messages.append(bad)
    with TestClient(create_app(settings, store)) as client:
        raw, headers = signed(settings, event)
        assert client.post("/webhook/whatsapp", content=raw, headers=headers).status_code == 400
    assert store.claim() is None
