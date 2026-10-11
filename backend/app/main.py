from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.middleware import SafetyMiddleware
from app.api.routes import router
from app.config import Settings
from app.errors import AppError
from app.services.extract.media import MediaExtractor
from app.services.extract.url import SafeFetcher
from app.services.providers import LLM, GeminiLLM
from app.services.search.client import SearchProvider, TavilySearch
from app.services.search.ledger import Ledger
from app.services.verify.engine import Verifier


def create_app(
    settings: Settings | None = None,
    llm: LLM | None = None,
    search: SearchProvider | None = None,
    fetcher: SafeFetcher | None = None,
    media: MediaExtractor | None = None,
) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="TruthLens AI Backend",
        version="0.1.0",
        description="Atomic claims, real source evidence and accessible explanations. Live verification requires configured providers.",
    )
    app.state.settings = settings
    app.state.llm = llm or GeminiLLM(settings)
    app.state.fetcher = fetcher or SafeFetcher(settings)
    app.state.media = media or MediaExtractor(
        settings, provider=app.state.llm if isinstance(app.state.llm, GeminiLLM) else None
    )
    app.state.verifier = Verifier(
        settings,
        app.state.llm,
        Ledger(settings, search or TavilySearch(settings), app.state.fetcher),
    )
    app.add_middleware(SafetyMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    def error(request: Request, code: str, message: str, status: int, details=None):
        value = {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        }
        if details is not None:
            value["details"] = details
        return JSONResponse({"error": value}, status_code=status)

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        response = error(request, exc.code, exc.message, exc.status)
        if exc.retry_after_seconds is not None:
            response.headers["Retry-After"] = str(exc.retry_after_seconds)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Pydantic's input/ctx fields may include forwarded messages or secrets.
        details = [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
        return error(
            request,
            "validation_error",
            "Check the request fields and supported values.",
            422,
            details,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error(
            request, "http_error", "This route or request is not supported.", exc.status_code
        )

    app.include_router(router)
    return app


app = create_app()
