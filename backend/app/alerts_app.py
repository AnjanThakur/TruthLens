"""Separate, opt-in alerts API. The existing verification app is unchanged."""

import asyncio
import hmac
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import AppError
from app.services.alerts.engine import AlertEngine
from app.services.alerts.models import (
    AlertDraft,
    ApproveRequest,
    Cluster,
    DraftRequest,
    EditRequest,
    ExportPayload,
    IngestRequest,
    IngestResponse,
    RejectRequest,
    VersionRequest,
    WithdrawRequest,
)
from app.services.alerts.settings import AlertsSettings

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)
MAX_BODY_BYTES = 262144


class AlertsBoundary:
    """Bound actual request bytes/time and prohibit caching sensitive responses."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = finished = False

        async def protected_send(message: Message) -> None:
            nonlocal started, finished
            if message["type"] == "http.response.start":
                started = True
                message["headers"] = [
                    *message.get("headers", []),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-request-id", request_id.encode()),
                ]
            elif message["type"] == "http.response.body":
                finished = not message.get("more_body", False)
            await send(message)

        async def invoke(input_receive: Receive) -> None:
            try:
                await self.app(scope, input_receive, protected_send)
            except Exception as exc:
                # Handle inside the boundary: Starlette's outer 500 handler re-raises
                # exceptions, allowing the server to print their private messages.
                logger.error("Alerts operation failed: exception_type=%s", type(exc).__name__)
                if not started:
                    response = JSONResponse(
                        status_code=500,
                        content={
                            "error": {
                                "code": "alerts_internal_error",
                                "message": "Alerts operation could not complete.",
                                "request_id": request_id,
                            }
                        },
                    )
                    await response(scope, input_receive, protected_send)
                elif not finished:
                    await protected_send(
                        {"type": "http.response.body", "body": b"", "more_body": False}
                    )

        if scope["method"] in {"POST", "PATCH", "PUT"}:
            body = bytearray()

            async def read_body() -> None:
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        raise AppError(
                            "alerts_request_incomplete", "Request body is incomplete.", 400
                        )
                    body.extend(message.get("body", b""))
                    if len(body) > MAX_BODY_BYTES:
                        raise AppError(
                            "alerts_request_too_large",
                            "Request exceeds the alerts body limit.",
                            413,
                        )
                    if not message.get("more_body", False):
                        return

            try:
                await asyncio.wait_for(read_body(), timeout=10)
            except (AppError, TimeoutError) as exc:
                error = (
                    exc
                    if isinstance(exc, AppError)
                    else AppError("alerts_request_timeout", "Request body timed out.", 408)
                )
                response = JSONResponse(
                    status_code=error.status,
                    content={
                        "error": {
                            "code": error.code,
                            "message": error.message,
                            "request_id": request_id,
                        }
                    },
                )
                await response(scope, receive, protected_send)
                return
            consumed = False

            async def replay() -> Message:
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await invoke(replay)
        else:
            await invoke(receive)


def create_alerts_app(
    settings: AlertsSettings | None = None, engine: AlertEngine | None = None
) -> FastAPI:
    if settings is None:
        try:
            settings = engine.settings if engine else AlertsSettings()
        except ValidationError:
            raise RuntimeError(
                "Invalid alerts configuration; check secret strength and bounded settings."
            ) from None
    engine = engine or AlertEngine(settings)
    if engine.settings != settings:
        raise ValueError("Alerts API and engine must use the same configuration.")

    async def sweeper() -> None:
        while True:
            await asyncio.sleep(settings.purge_interval_seconds)
            try:
                await asyncio.to_thread(engine.purge)
            except Exception as exc:
                logger.error("Alerts retention sweep failed: exception_type=%s", type(exc).__name__)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            engine.purge()
        except Exception as exc:
            logger.error("Alerts initialization failed: exception_type=%s", type(exc).__name__)
            raise RuntimeError("Unable to initialize the alerts repository.") from None
        task = asyncio.create_task(sweeper())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    application = FastAPI(
        title="TruthLens Scam Alert Intelligence", version="0.1.0", lifespan=lifespan
    )
    application.state.alert_engine = engine
    application.add_middleware(AlertsBoundary)

    def authorize(role: str) -> Callable:
        def check(
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        ) -> None:
            if not settings.configured:
                raise AppError(
                    "alerts_not_configured", "Alerts authentication is not configured.", 503
                )
            if credentials is None or credentials.scheme.lower() != "bearer":
                raise AppError(
                    "alerts_unauthorized", "A service bearer credential is required.", 401
                )
            supplied = credentials.credentials
            ingest = hmac.compare_digest(
                supplied.encode(), settings.ingest_token.get_secret_value().encode()
            )
            admin = hmac.compare_digest(
                supplied.encode(), settings.admin_token.get_secret_value().encode()
            )
            if not ingest and not admin:
                raise AppError("alerts_unauthorized", "Invalid service credential.", 401)
            if role == "ingest" and not ingest or role == "admin" and not admin:
                raise AppError(
                    "alerts_forbidden", "Credential is not authorized for this operation.", 403
                )

        return check

    ingest_auth, admin_auth = Depends(authorize("ingest")), Depends(authorize("admin"))

    @application.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        return JSONResponse(
            status_code=exc.status,
            headers=headers,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic input/context/locations can include private content; never echo them.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "alerts_validation_error",
                    "message": "Invalid alerts request; consult the schema.",
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Alerts operation failed: exception_type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            headers={"Cache-Control": "no-store"},
            content={
                "error": {
                    "code": "alerts_internal_error",
                    "message": "Alerts operation could not complete.",
                    "request_id": getattr(request.state, "request_id", str(uuid4())),
                }
            },
        )

    @application.get("/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "configured": settings.configured,
            "storage": "repository_adapter",
            "publishing": False,
        }

    @application.post(
        "/api/alerts/ingest", response_model=IngestResponse, dependencies=[ingest_auth]
    )
    def ingest(payload: IngestRequest) -> IngestResponse:
        return engine.ingest(payload)

    @application.post("/api/alerts/withdraw", dependencies=[ingest_auth])
    def withdraw(payload: WithdrawRequest) -> dict[str, int]:
        return {"deleted_observations": engine.withdraw(payload.source_token.get_secret_value())}

    @application.get(
        "/api/alerts/clusters", response_model=list[Cluster], dependencies=[admin_auth]
    )
    def clusters() -> list[Cluster]:
        return engine.clusters()

    @application.get(
        "/api/alerts/drafts", response_model=list[AlertDraft], dependencies=[admin_auth]
    )
    def drafts() -> list[AlertDraft]:
        return engine.drafts()

    @application.post("/api/alerts/purge", dependencies=[admin_auth])
    def purge() -> dict[str, int]:
        return {"deleted_observations": engine.purge()}

    @application.post(
        "/api/alerts/clusters/{cluster_id}/drafts",
        response_model=AlertDraft,
        dependencies=[admin_auth],
    )
    def create_draft(cluster_id: UUID, payload: DraftRequest) -> AlertDraft:
        return engine.create_draft(cluster_id, payload.language)

    @application.patch(
        "/api/alerts/{alert_id}", response_model=AlertDraft, dependencies=[admin_auth]
    )
    def edit(alert_id: UUID, payload: EditRequest) -> AlertDraft:
        return engine.edit(alert_id, payload)

    @application.post(
        "/api/alerts/{alert_id}/submit", response_model=AlertDraft, dependencies=[admin_auth]
    )
    def submit(alert_id: UUID, payload: VersionRequest) -> AlertDraft:
        return engine.submit(alert_id, payload.expected_version)

    @application.post(
        "/api/alerts/{alert_id}/approve", response_model=AlertDraft, dependencies=[admin_auth]
    )
    def approve(alert_id: UUID, payload: ApproveRequest) -> AlertDraft:
        return engine.approve(alert_id, payload)

    @application.post(
        "/api/alerts/{alert_id}/reject", response_model=AlertDraft, dependencies=[admin_auth]
    )
    def reject(alert_id: UUID, payload: RejectRequest) -> AlertDraft:
        return engine.reject(alert_id, payload)

    @application.get(
        "/api/alerts/{alert_id}/export", response_model=ExportPayload, dependencies=[admin_auth]
    )
    def export(alert_id: UUID) -> ExportPayload:
        return engine.export(alert_id)

    return application


app = create_alerts_app()
