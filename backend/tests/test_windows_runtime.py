import importlib.util
from pathlib import Path

import pytest
from dotenv import dotenv_values

SPEC = importlib.util.spec_from_file_location(
    "truthlens_local_runtime", Path(__file__).resolve().parents[2] / "scripts" / "runtime.py"
)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


@pytest.fixture(autouse=True)
def isolated_runtime_environment(monkeypatch):
    # configure() intentionally mutates process environment. delenv() cannot undo
    # a new key that was absent when the test began, so isolate the entire mapping.
    monkeypatch.setattr(runtime.os, "environ", runtime.os.environ.copy())


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
def test_preview_origin_keeps_the_selected_cookie_host_and_port(host):
    origin = f"http://{host}:3001"
    assert runtime.website_origin(3001, origin) == origin
    assert runtime.website_origin(3001) == "http://127.0.0.1:3001"


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3000",
        "https://attacker.example",
        "http://localhost:3001/auth/callback",
        "http://user:secret@localhost:3001",
        "http://localhost:3001?redirect=http://localhost:3000",
    ],
)
def test_preview_origin_rejects_other_ports_paths_credentials_and_external_hosts(origin):
    with pytest.raises(ValueError):
        runtime.website_origin(3001, origin)


def test_runtime_preserves_private_keys_and_absolutizes_original_whatsapp_state(
    tmp_path, monkeypatch
):
    private, project = tmp_path / "private", tmp_path / "feature"
    adapter = private / "whatsapp-adapter"
    adapter.mkdir(parents=True)
    original = "DATABASE_URL=sqlite:///state/existing.sqlite3\nSTATE_ENCRYPTION_KEY=private-stable-key\nTWILIO_OUTBOUND_ENABLED=true\nBACKEND_ENABLED=true\nRESPONSE_MODE=backend\n"
    (adapter / ".env.twilio").write_text(original)
    monkeypatch.setattr(runtime, "initialize", lambda *args: {})
    for key in (
        "DATABASE_URL",
        "STATE_ENCRYPTION_KEY",
        "TWILIO_OUTBOUND_ENABLED",
        "META_OUTBOUND_ENABLED",
        "BACKEND_ENABLED",
        "RESPONSE_MODE",
    ):
        monkeypatch.delenv(key, raising=False)
    runtime.configure(project, private, "worker", False)
    assert runtime.os.environ["DATABASE_URL"] == "sqlite:///" + str(
        (adapter / "state" / "existing.sqlite3").resolve()
    )
    assert runtime.os.environ["STATE_ENCRYPTION_KEY"] == "private-stable-key"
    assert runtime.os.environ["TWILIO_OUTBOUND_ENABLED"] == "false"
    assert runtime.os.environ["BACKEND_ENABLED"] == "false"
    assert (adapter / ".env.twilio").read_text() == original
    assert not (adapter / "state").exists()


def test_runtime_default_blanks_provider_keys_and_local_secrets_survive_restart(
    tmp_path, monkeypatch
):
    private, project = tmp_path / "private", tmp_path / "feature"
    backend = private / "backend"
    backend.mkdir(parents=True)
    (backend / ".env").write_text(
        "GEMINI_API_KEY=private-fixture\nTAVILY_API_KEY=private-fixture\n"
    )
    for key in (
        "GEMINI_API_KEY",
        "TAVILY_API_KEY",
        "ALERTS_ENCRYPTION_KEY",
        "ALERTS_DATABASE_PATH",
        "ALERTS_INGEST_TOKEN",
        "ALERTS_ADMIN_TOKEN",
        "ALERTS_PSEUDONYM_SECRET",
        "ALERTS_SOURCE_SECRET",
        "HISTORY_SIGNING_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    first = runtime.initialize(project, private)
    assert first == runtime.initialize(project, private)
    saved = dotenv_values(project / ".tmp" / "runtime" / "secrets.env")
    assert first == saved and first["ALERTS_DATABASE_PATH"] == str(
        project / "backend" / "state" / "alerts.sqlite3"
    )
    runtime.configure(project, private, "backend", False)
    assert not runtime.os.environ["GEMINI_API_KEY"] and not runtime.os.environ["TAVILY_API_KEY"]
    assert "private-fixture" in (backend / ".env").read_text()


def test_controlled_acceptance_has_process_wide_attempt_ceilings(monkeypatch):
    from app.errors import AppError

    monkeypatch.setenv("GEMINI_API_KEY", "fixture-not-a-key")
    monkeypatch.setenv("TAVILY_API_KEY", "fixture-not-a-key")
    app, llm, search = runtime.acceptance_app()
    assert app.state.settings.max_claims == 1
    assert app.state.settings.max_search_queries_per_claim == 2
    for _ in range(5):
        llm.reserve_request()
    with pytest.raises(AppError, match="budget"):
        llm.reserve_request()
    for _ in range(2):
        search.reserve_request()
    with pytest.raises(AppError, match="budget"):
        search.reserve_request()
    assert (llm.request_count, search.request_count) == (5, 2)
