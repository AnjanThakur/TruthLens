"""Local Windows service runner. Startup never enables providers or outbound sending by default."""

import argparse
import json
import logging
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from dotenv import dotenv_values

SERVICES = {
    "backend": ("backend", 8000),
    "alerts": ("backend", 8001),
    "adapter": ("whatsapp-adapter", 8100),
    "website": ("frontend", 3000),
    "worker": ("whatsapp-adapter", 0),
    "ngrok": ("whatsapp-adapter", 4040),
}


def private_root(project: Path, value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    candidate = project.parents[1] if project.parent.name == ".worktrees" else project
    return candidate.resolve()


def initialize(project: Path, private: Path) -> dict[str, str]:
    directory = project / ".tmp" / "runtime"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "secrets.env"
    if target.exists():
        saved = {k: v for k, v in dotenv_values(target).items() if v}
        if not saved.get("ALERTS_DATABASE_PATH") or any(
            ord(char) < 32 for char in saved["ALERTS_DATABASE_PATH"]
        ):
            raise ValueError(
                "Restore the existing alert storage path without changing its stable keys"
            )
        return saved
    existing = {
        **dotenv_values(private / "backend" / ".env"),
        **dotenv_values(private / "frontend" / ".env.local"),
    }
    names = (
        # Existing storage cannot be paired with a newly generated replacement key.
        "ALERTS_INGEST_TOKEN",
        "ALERTS_ADMIN_TOKEN",
        "ALERTS_PSEUDONYM_SECRET",
        "ALERTS_SOURCE_SECRET",
        "HISTORY_SIGNING_SECRET",
    )
    if bool(existing.get("ALERTS_DATABASE_PATH")) != bool(
        existing.get("ALERTS_ENCRYPTION_KEY")
    ):
        raise ValueError(
            "Existing alert storage requires its original paired encryption key"
        )
    if (project / "backend" / "state" / "alerts.sqlite3").exists() and not existing.get(
        "ALERTS_ENCRYPTION_KEY"
    ):
        raise ValueError(
            "Restore the original alert encryption key before using existing state"
        )
    values = {key: existing.get(key) or secrets.token_hex(32) for key in names}
    values["ALERTS_ENCRYPTION_KEY"] = (
        existing.get("ALERTS_ENCRYPTION_KEY") or Fernet.generate_key().decode()
    )
    values["ALERTS_DATABASE_PATH"] = existing.get("ALERTS_DATABASE_PATH") or str(
        project / "backend" / "state" / "alerts.sqlite3"
    )
    # Exclusive creation prevents concurrent startup from replacing stable keys.
    try:
        with target.open("x", encoding="utf-8") as stream:
            stream.write(
                "\n".join(
                    f"{key}={json.dumps(value, ensure_ascii=False)}"
                    for key, value in values.items()
                )
                + "\n"
            )
    except FileExistsError:
        return {k: v for k, v in dotenv_values(target).items() if v}
    return values


def configure(project: Path, private: Path, service: str, providers: bool) -> Path:
    directory = project / SERVICES[service][0]
    envfile = (
        private
        / SERVICES[service][0]
        / (
            ".env.twilio"
            if service in {"adapter", "worker", "ngrok"}
            else ".env.local"
            if service == "website"
            else ".env"
        )
    )
    for key, value in dotenv_values(envfile).items():
        if value is not None:
            os.environ[key] = value
    for key, value in initialize(project, private).items():
        os.environ.setdefault(key, value)
    if service in {"backend", "alerts"}:
        if not providers:
            os.environ["GEMINI_API_KEY"] = os.environ["TAVILY_API_KEY"] = ""
        for key in ("TESSDATA_DIR", "TESSERACT_CMD", "FFMPEG_CMD", "FFPROBE_CMD"):
            value = os.environ.get(key, "")
            if (
                value
                and not Path(value).is_absolute()
                and ("/" in value or "\\" in value)
            ):
                os.environ[key] = str((private / "backend" / value).resolve())
        if (
            not os.environ.get("TESSDATA_DIR")
            and (private / "backend" / ".runtime" / "tessdata").exists()
        ):
            os.environ["TESSDATA_DIR"] = str(
                private / "backend" / ".runtime" / "tessdata"
            )
    elif service == "website":
        os.environ.setdefault("BACKEND_BASE_URL", "http://127.0.0.1:8000")
        os.environ.setdefault("ALERTS_BASE_URL", "http://127.0.0.1:8001")
        os.environ["USE_MOCK_API"] = os.environ["NEXT_PUBLIC_USE_MOCK_API"] = "false"
    elif service in {"adapter", "worker"}:
        os.environ["TRUTHLENS_ENV_FILE"] = str(envfile)
        url = os.environ.get("DATABASE_URL", "sqlite:///state/bot.sqlite3")
        if url.startswith("sqlite:///"):
            path = Path(url.removeprefix("sqlite:///"))
            if not path.is_absolute():
                os.environ["DATABASE_URL"] = "sqlite:///" + str(
                    (envfile.parent / path).resolve()
                )
        # The HTTP adapter still records signed callbacks; no send or queue claim is enabled.
        os.environ["TWILIO_OUTBOUND_ENABLED"] = os.environ["META_OUTBOUND_ENABLED"] = (
            "false"
        )
        os.environ["BACKEND_ENABLED"] = "false"
        os.environ["RESPONSE_MODE"] = "development"
    return directory


def preflight(
    project: Path, private: Path, service: str, providers: bool, port: int
) -> dict:
    directory = configure(project, private, service, providers)
    sys.path.insert(0, str(directory))
    result = {
        "service": service,
        "status": "PASS",
        "port": port,
        "providers_enabled": providers if service == "backend" else False,
        "outbound_enabled": False,
    }
    if service == "backend":
        from app.config import Settings
        from app.services.extract.media import capabilities

        settings = Settings(_env_file=None)
        result["native_capabilities"] = capabilities(settings)
        if providers and not (
            settings.gemini_api_key.get_secret_value()
            and settings.tavily_api_key.get_secret_value()
        ):
            raise ValueError("Provider configuration missing")
    elif service == "alerts":
        from app.services.alerts.settings import AlertsSettings

        settings = AlertsSettings(_env_file=None)
        if not settings.configured or not settings.database_path:
            raise ValueError("Durable alert configuration missing")
        wa_url = (
            dotenv_values(private / "whatsapp-adapter" / ".env.twilio").get(
                "DATABASE_URL", "sqlite:///state/bot.sqlite3"
            )
            or ""
        )
        if wa_url.startswith("sqlite:///"):
            wa_path = Path(wa_url.removeprefix("sqlite:///"))
            if not wa_path.is_absolute():
                wa_path = private / "whatsapp-adapter" / wa_path
            if Path(settings.database_path).resolve() == wa_path.resolve():
                raise ValueError(
                    "Alerts must use a database isolated from WhatsApp state"
                )
        result["storage"] = "isolated_encrypted_sqlite"
    elif service in {"adapter", "worker"}:
        from truthlens_whatsapp.config import Settings

        settings = Settings(_env_file=None)
        result["provider"] = settings.messaging_provider
        result["worker"] = "paused"
    elif service == "website":
        if (
            not shutil.which("node")
            or not (
                directory / "node_modules" / "next" / "dist" / "bin" / "next"
            ).exists()
            or not (directory / ".next" / "BUILD_ID").exists()
        ):
            raise ValueError("Install frontend dependencies and build first")
        result["supabase_configured"] = bool(
            os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            and os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
        )
    elif service == "ngrok":
        if not shutil.which("ngrok"):
            raise ValueError("ngrok executable missing")
    if port:
        with socket.socket() as connection:
            connection.settimeout(0.3)
            result["port_in_use"] = connection.connect_ex(("127.0.0.1", port)) == 0
    return result


def acceptance_app():
    """One process-wide approved acceptance budget, including actual retry attempts."""
    from app.config import Settings
    from app.main import create_app
    from scripts.validate_live import BudgetedGemini, BudgetedSearch

    settings = Settings(_env_file=None)
    settings.max_claims = 1
    settings.max_evidence = 3
    settings.max_search_queries_per_claim = 2
    settings.max_search_attempts_per_check = 2
    settings.max_llm_attempts_per_check = 5
    llm, search = BudgetedGemini(settings), BudgetedSearch(settings)
    llm.budget, search.budget = 5, 2
    return create_app(settings, llm, search), llm, search


def run(args) -> None:
    project = Path(args.project).resolve()
    private = private_root(project, args.private)
    service = args.service
    port = args.port if args.port is not None else SERVICES[service][1]
    if args.controlled_acceptance and service != "backend":
        raise ValueError("Controlled provider acceptance is backend-only")
    result = preflight(
        project,
        private,
        service,
        args.providers_enabled or args.controlled_acceptance,
        port,
    )
    if args.controlled_acceptance:
        result["acceptance_ceilings"] = {"gemini": 5, "tavily": 2, "twilio": 0}
    if args.check:
        print(json.dumps(result))
        return
    if result.get("port_in_use"):
        raise ValueError("Port occupied; no existing process was stopped")
    directory = project / SERVICES[service][0]
    os.chdir(directory)
    identity = str(UUID(args.instance)) if args.instance else str(uuid4())
    runtime = project / ".tmp" / "runtime"
    stop = runtime / (identity + ".stop")
    record = runtime / (identity + ".json")
    record.write_text(
        json.dumps(
            {
                "instance": identity,
                "pid": os.getpid(),
                "service": service,
                "port": port,
                "started_at": datetime.now(UTC).isoformat(),
                "state": "starting",
            }
        ),
        encoding="utf-8",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    child = None
    server = None
    counters = None
    if service == "website":
        os.environ["APP_ORIGIN"] = f"http://127.0.0.1:{port}"
        command = [
            shutil.which("node"),
            str(directory / "node_modules" / "next" / "dist" / "bin" / "next"),
            "start",
            "--hostname",
            "127.0.0.1",
            "--port",
            str(port),
        ]
        child = subprocess.Popen(  # noqa: S603 - fixed local executable, shell disabled.
            command, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
    elif service == "ngrok":
        child = subprocess.Popen(  # noqa: S603 - fixed local executable, shell disabled.
            [shutil.which("ngrok"), "http", "8100", "--log", "stdout"],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    elif service != "worker":
        import uvicorn

        module = {
            "backend": "app.main:app",
            "alerts": "app.alerts_app:app",
            "adapter": "truthlens_whatsapp.main:app",
        }[service]
        if args.controlled_acceptance:
            module, llm, search = acceptance_app()
            counters = (llm, search)

        server = uvicorn.Server(
            uvicorn.Config(
                module,
                host="127.0.0.1",
                port=port,
                access_log=False,
                log_level="warning",
            )
        )

        def watch():
            while not stop.exists() and not server.should_exit:
                if counters:
                    (runtime / (identity + ".acceptance.json")).write_text(
                        json.dumps(
                            {
                                "gemini_attempts": counters[0].request_count,
                                "tavily_attempts": counters[1].request_count,
                                "twilio_attempts": 0,
                            }
                        ),
                        encoding="utf-8",
                    )
                time.sleep(0.2)
            server.should_exit = True

        threading.Thread(target=watch, daemon=True).start()
    record.write_text(
        json.dumps(
            {
                "instance": identity,
                "pid": os.getpid(),
                "service": service,
                "port": port,
                "started_at": datetime.now(UTC).isoformat(),
                "state": "paused" if service == "worker" else "running",
            }
        ),
        encoding="utf-8",
    )
    try:
        if server:
            server.run()
        else:
            while not stop.exists() and (child is None or child.poll() is None):
                time.sleep(0.2)
    finally:
        if counters:
            (runtime / (identity + ".acceptance.json")).write_text(
                json.dumps(
                    {
                        "gemini_attempts": counters[0].request_count,
                        "tavily_attempts": counters[1].request_count,
                        "twilio_attempts": 0,
                    }
                ),
                encoding="utf-8",
            )
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        record.write_text(
            json.dumps(
                {
                    "instance": identity,
                    "pid": os.getpid(),
                    "service": service,
                    "port": port,
                    "state": "stopped",
                }
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--private")
    parser.add_argument("--service", choices=SERVICES, required=True)
    parser.add_argument("--port", type=int)
    parser.add_argument("--instance")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--providers-enabled", action="store_true")
    parser.add_argument("--controlled-acceptance", action="store_true")
    try:
        run(parser.parse_args())
    except Exception as error:  # noqa: BLE001 - top-level diagnostics must never expose private settings.
        # Pydantic/subprocess diagnostics can contain private env values: never print them.
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": "runtime_configuration_or_dependency_error",
                    "exception_type": type(error).__name__,
                }
            )
        )
        raise SystemExit(1) from None
