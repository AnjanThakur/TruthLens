from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.errors import AppError
from app.services.alerts.engine import AlertEngine
from app.services.alerts.models import IngestRequest
from app.services.alerts.repository import Receipt
from app.services.alerts.settings import AlertsSettings
from app.services.alerts.sqlite_repository import SQLiteAlertRepository
from scripts.demo_alerts import fixture_record


def test_restart_encryption_and_withdrawal(tmp_path):
    path, key = tmp_path / "isolated-alerts.sqlite3", Fernet.generate_key().decode()
    settings = AlertsSettings(
        _env_file=None,
        ingest_token="i" * 40,
        admin_token="a" * 40,
        pseudonym_secret="p" * 40,
        database_path=str(path),
        encryption_key=key,
    )
    instant = datetime(2026, 10, 11, 8, tzinfo=UTC)
    source = str(uuid4())
    record = fixture_record(instant)
    engine = AlertEngine(settings, clock=lambda: instant)
    engine.ingest(
        IngestRequest(consent=True, source_token=source, submission_id=uuid4(), verification=record)
    )
    restarted = AlertEngine(settings, clock=lambda: instant)
    assert len(restarted.clusters()) == 1
    # Neither the source token nor submitted text may be recoverable as plaintext.
    assert source.encode() not in path.read_bytes()
    assert record.claims[0].claim_text.encode() not in path.read_bytes()
    restarted.withdraw(source)
    assert not AlertEngine(settings, clock=lambda: instant).clusters()


def test_retention_purge_is_durable_after_restart(tmp_path):
    settings = AlertsSettings(
        _env_file=None,
        ingest_token="i" * 40,
        admin_token="a" * 40,
        pseudonym_secret="p" * 40,
        database_path=str(tmp_path / "retention.sqlite3"),
        encryption_key=Fernet.generate_key().decode(),
    )
    instant = datetime(2026, 10, 11, 8, tzinfo=UTC)
    original = AlertEngine(settings, clock=lambda: instant)
    for language in ("en", "hi", "mr"):
        original.ingest(
            IngestRequest(
                consent=True,
                source_token=str(uuid4()),
                submission_id=uuid4(),
                verification=fixture_record(instant, language),
            )
        )
    with original.repository.transaction() as state:
        assert len(state.observations) == len(state.receipts) == 3
        assert state.clusters and state.drafts
    expired = instant + timedelta(days=settings.retention_days + 1)
    restarted = AlertEngine(settings, clock=lambda: expired)
    assert restarted.purge() == 3
    again = AlertEngine(settings, clock=lambda: expired)
    with again.repository.transaction() as state:
        assert not state.observations and not state.receipts
        assert not state.clusters and not state.drafts


def test_atomic_rollback_and_key_mismatch_fail_closed(tmp_path):
    path, key = tmp_path / "alerts.sqlite3", Fernet.generate_key().decode()
    repository = SQLiteAlertRepository(str(path), key)
    item = uuid4()
    with pytest.raises(RuntimeError):
        with repository.transaction() as state:
            state.receipts[item] = Receipt("hash", "digest", [], datetime.now(UTC))
            raise RuntimeError("abort")
    with repository.transaction() as state:
        assert not state.receipts
        state.receipts[item] = Receipt("hash", "digest", [], datetime.now(UTC))
    wrong_key = SQLiteAlertRepository(str(path), Fernet.generate_key().decode())
    with pytest.raises(AppError) as caught:
        with wrong_key.transaction():
            pass
    assert caught.value.code == "alerts_storage_unavailable" and key not in str(caught.value)
    with repository.transaction() as state:
        assert item in state.receipts


def test_independent_instances_serialize_transactions(tmp_path):
    path, key = tmp_path / "alerts.sqlite3", Fernet.generate_key().decode()
    repositories = [SQLiteAlertRepository(str(path), key) for _ in range(2)]

    def insert(index):
        with repositories[index % 2].transaction() as state:
            state.receipts[uuid4()] = Receipt("hash", "digest", [], datetime.now(UTC))

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(insert, range(20)))
    with repositories[0].transaction() as state:
        assert len(state.receipts) == 20


@pytest.mark.parametrize(
    "kwargs",
    [
        {"database_path": "private.sqlite3"},
        {"encryption_key": "invalid"},
        {"database_path": "private.sqlite3", "encryption_key": "invalid"},
    ],
)
def test_storage_requires_paired_valid_key(kwargs):
    with pytest.raises(ValidationError):
        AlertsSettings(_env_file=None, **kwargs)
