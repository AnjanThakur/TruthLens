"""Encrypted, atomic local persistence, isolated from verification and WhatsApp databases."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from pydantic import ValidationError

from app.errors import AppError
from app.services.alerts.models import AlertDraft, Cluster, Observation
from app.services.alerts.repository import AlertState, Receipt


class SQLiteAlertRepository:
    def __init__(self, path: str, key: str):
        self.path = Path(path).resolve()
        self.cipher = Fernet(key.encode("ascii"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS alert_state (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def _decode(self, encrypted: bytes) -> AlertState:
        try:
            value = json.loads(self.cipher.decrypt(encrypted))
            if value["version"] != 1:
                raise ValueError
            return AlertState(
                observations={
                    UUID(k): Observation.model_validate(v) for k, v in value["observations"].items()
                },
                clusters={UUID(k): Cluster.model_validate(v) for k, v in value["clusters"].items()},
                drafts={UUID(k): AlertDraft.model_validate(v) for k, v in value["drafts"].items()},
                receipts={
                    UUID(k): Receipt(
                        v["source_hash"],
                        v["digest"],
                        [UUID(item) for item in v["cluster_ids"]],
                        datetime.fromisoformat(v["received_at"]),
                    )
                    for k, v in value["receipts"].items()
                },
            )
        except (InvalidToken, ValidationError, ValueError, KeyError, TypeError, AttributeError):
            raise AppError(
                "alerts_storage_unavailable",
                "Alert state could not be read safely. Preserve the database and encryption key.",
                503,
            ) from None

    def _encode(self, state: AlertState) -> bytes:
        payload = {
            "version": 1,
            "observations": {
                str(k): v.model_dump(mode="json") for k, v in state.observations.items()
            },
            "clusters": {str(k): v.model_dump(mode="json") for k, v in state.clusters.items()},
            "drafts": {str(k): v.model_dump(mode="json") for k, v in state.drafts.items()},
            "receipts": {
                str(k): {
                    "source_hash": v.source_hash,
                    "digest": v.digest,
                    "cluster_ids": [str(item) for item in v.cluster_ids],
                    "received_at": v.received_at.isoformat(),
                }
                for k, v in state.receipts.items()
            },
        }
        return self.cipher.encrypt(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    @contextmanager
    def transaction(self) -> Iterator[AlertState]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT payload FROM alert_state WHERE id=1").fetchone()
            state = self._decode(row[0]) if row else AlertState()
            yield state
            connection.execute(
                "INSERT INTO alert_state(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (self._encode(state),),
            )
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise AppError(
                "alerts_storage_unavailable", "Alert storage is temporarily unavailable.", 503
            ) from None
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
