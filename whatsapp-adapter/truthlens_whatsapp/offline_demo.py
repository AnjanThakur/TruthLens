"""Signed webhook → durable worker → mocked Meta send. Zero external HTTP calls."""

import asyncio
import hashlib
import hmac
import json
import secrets
import tempfile
import time
from pathlib import Path

import httpx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from .config import Settings
from .main import create_app
from .meta_client import MetaClient
from .store import Store
from .truthlens_client import TruthLensClient
from .worker import Worker


async def demo():
    Path(".tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".tmp") as directory:
        settings = Settings(
            _env_file=None,
            meta_app_secret=secrets.token_urlsafe(32),
            whatsapp_verify_token=secrets.token_urlsafe(32),
            whatsapp_phone_number_id="12345",
            whatsapp_waba_id="67890",
            identity_hash_secret=secrets.token_urlsafe(32),
            state_encryption_key=Fernet.generate_key().decode(),
            database_url=f"sqlite:///{Path(directory).resolve() / 'demo.db'}",
            graph_api_version="v99.0",
            whatsapp_access_token="OFFLINE_ONLY",
            meta_outbound_enabled=True,
        )
        store = Store(settings)
        sends = []

        def mocked_meta(request):
            assert request.url.host == "graph.facebook.com"
            sends.append(json.loads(request.content))
            return httpx.Response(200, json={"messages": [{"id": "wamid.offline-reply"}]})

        message = {
            "id": "wamid.offline-demo",
            "from": "15550000001",
            "timestamp": str(int(time.time())),
            "type": "text",
            "text": {"body": "Offline routing demonstration"},
        }
        event = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": settings.whatsapp_waba_id,
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "metadata": {"phone_number_id": settings.whatsapp_phone_number_id},
                                "messages": [message],
                            },
                        }
                    ],
                }
            ],
        }
        raw = json.dumps(event).encode()
        signature = hmac.new(
            settings.meta_app_secret.get_secret_value().encode(), raw, hashlib.sha256
        ).hexdigest()
        with TestClient(create_app(settings, store)) as webhook:
            for _ in range(2):
                assert (
                    webhook.post(
                        "/webhook/whatsapp",
                        content=raw,
                        headers={"X-Hub-Signature-256": f"sha256={signature}"},
                    ).status_code
                    == 200
                )
            async with httpx.AsyncClient(transport=httpx.MockTransport(mocked_meta)) as http:
                worker = Worker(
                    settings, store, MetaClient(settings, http), TruthLensClient(settings, http)
                )
                assert await worker.process_one()
                assert not await worker.process_one()
                assert await worker.send_one()
                assert not await worker.send_one()
        assert len(sends) == 1
        print(
            "PASS: signed local webhook, durable deduplication, worker, exactly one MOCKED Meta send."
        )
        print(
            "No real WhatsApp delivery, AI verification, Meta account or provider credits were used."
        )
        print(sends[0]["text"]["body"])


if __name__ == "__main__":
    asyncio.run(demo())
