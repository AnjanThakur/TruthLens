from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.services.alerts.models import AlertDraft, Cluster, Observation


@dataclass
class Receipt:
    source_hash: str
    digest: str
    cluster_ids: list[UUID]
    received_at: datetime


@dataclass
class AlertState:
    observations: dict[UUID, Observation] = field(default_factory=dict)
    clusters: dict[UUID, Cluster] = field(default_factory=dict)
    drafts: dict[UUID, AlertDraft] = field(default_factory=dict)
    receipts: dict[UUID, Receipt] = field(default_factory=dict)


class AlertRepository(Protocol):
    def transaction(self) -> AbstractContextManager[AlertState]: ...


class MemoryAlertRepository:
    """Bounded service state, atomic rollback, copy isolation; ephemeral single-worker dev adapter."""

    def __init__(self):
        self._state = AlertState()
        self._lock = RLock()

    @contextmanager
    def transaction(self) -> Iterator[AlertState]:
        with self._lock:
            working = deepcopy(self._state)
            yield working
            self._state = deepcopy(working)
