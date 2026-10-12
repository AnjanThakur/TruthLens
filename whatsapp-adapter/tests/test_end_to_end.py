import copy
import json

import httpx
from fastapi.testclient import TestClient
from test_webhook import signed

from truthlens_whatsapp.main import create_app
from truthlens_whatsapp.meta_client import MetaClient
from truthlens_whatsapp.truthlens_client import TruthLensClient
from truthlens_whatsapp.worker import Worker


async def test_signed_webhook_to_real_clients_to_delivery(settings, store, event, report):
    settings.response_mode = "backend"
    settings.backend_enabled = settings.provider_credentials_rotated = True
    settings.meta_outbound_enabled = True
    calls = []

    def transport(request):
        calls.append(request)
        if request.url.path == "/api/verify":
            return httpx.Response(200, json=report)
        body = json.loads(request.content)
        assert body["messaging_product"] == "whatsapp"
        assert body["to"] == "15550000001"
        assert "https://example.test/source" in body["text"]["body"]
        return httpx.Response(200, json={"messages": [{"id": "wamid.outgoing"}]})

    with TestClient(create_app(settings, store)) as webhook:
        raw, headers = signed(settings, event)
        assert webhook.post("/webhook/whatsapp", content=raw, headers=headers).status_code == 200
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            worker = Worker(
                settings, store, MetaClient(settings, http), TruthLensClient(settings, http)
            )
            assert await worker.process_one()
            assert await worker.send_one()
            webhook.post("/webhook/whatsapp", content=raw, headers=headers)
            assert not await worker.process_one()
            assert not await worker.send_one()
        delivered = copy.deepcopy(event)
        value = delivered["entry"][0]["changes"][0]["value"]
        value.pop("messages")
        value["statuses"] = [{"id": "wamid.outgoing", "status": "delivered"}]
        raw, headers = signed(settings, delivered)
        assert webhook.post("/webhook/whatsapp", content=raw, headers=headers).status_code == 200
    assert len(calls) == 2
    with store.tx() as db:
        assert store.execute(db, "SELECT state FROM outbox").fetchone()["state"] == "delivered"
