import time

import pytest

from truthlens_whatsapp.errors import ServiceError
from truthlens_whatsapp.store import Store


def test_durable_encrypted_dedup(settings, store, message):
    store.enqueue([message])
    other = Store(settings)
    other.enqueue([message])
    job = other.claim()
    assert job and store.claim() is None
    assert store.open(job["payload"]) == message
    raw = settings.sqlite_path().read_bytes()
    assert message["from"].encode() not in raw
    assert message["text"]["body"].encode() not in raw
    other.finish(job["id"])
    store.enqueue([message])
    assert store.claim() is None


def test_atomic_rate_limit(settings, store, message):
    settings.per_sender_per_minute = 1
    other = {**message, "id": "wamid.second"}
    with pytest.raises(ServiceError, match="queue_busy"):
        store.enqueue([message, other])
    assert store.claim() is None


def test_optout_restart_and_retention(settings, store, message):
    message["text"]["body"] = "STOP"
    store.enqueue([message])
    sender = store.identity(message["from"])
    assert Store(settings).preference(sender)["stopped"] == 1
    job = store.claim()
    with store.tx() as db:
        store.execute(db, "UPDATE jobs SET lease=? WHERE id=?", (time.time() - 1, job["id"]))
    assert store.claim() is None  # Never repeats a possibly paid interrupted provider call.
    with store.tx() as db:
        store.execute(db, "UPDATE jobs SET created=?", (time.time() - 25 * 3600,))
    store.cleanup()
    with store.tx() as db:
        row = store.execute(db, "SELECT * FROM jobs").fetchone()
    assert row["payload"] is None and row["report"] is None
    assert row["state"] == "failed"


def test_outbox_order_and_delivery_reconciliation(store, message):
    store.enqueue([message])
    job = store.claim()
    store.prepare(job["id"], ["First", "Second"])
    store.prepare(job["id"], ["First", "Second"])
    item = store.next_send()
    assert store.next_send() is None
    store.send_state(item["id"], "uncertain")
    assert store.next_send() is None
    store.delivery(
        {"id": "wamid.reply", "status": "delivered", "biz_opaque_callback_data": item["id"]}
    )
    store.send_state(item["id"], "accepted", "wamid.reply")
    store.delivery({"id": "wamid.reply", "status": "sent"})
    assert store.next_send()["part"] == 1
    with store.tx() as db:
        assert (
            store.execute(db, "SELECT state FROM outbox WHERE id=?", (item["id"],)).fetchone()[
                "state"
            ]
            == "delivered"
        )
