import asyncio
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from app.errors import AppError
from app.schemas.models import (
    ErrorResponse,
    ExplainRequest,
    ExtractionResult,
    HealthResponse,
    URLRequest,
    VerificationResult,
    VerifyRequest,
)
from app.services.chunks import split_text
from app.services.common import detect_language, normalize
from app.services.explain.engine import reexplain
from app.services.extract.encoding import decode_web_text
from app.services.extract.media import capabilities
from app.services.extract.url import article_from_html

router = APIRouter(
    prefix="/api",
    responses={
        status: {"model": ErrorResponse} for status in (400, 413, 415, 422, 500, 502, 503, 504)
    },
)


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    settings = request.app.state.settings
    available = await asyncio.to_thread(capabilities, settings)
    return {
        "status": "ok",
        "capabilities": available,
        "dependencies": {
            "tesseract": available["ocr"],
            "ffmpeg": available["ffmpeg"],
            "ffprobe": available["ffprobe"],
            "pymupdf": available["pdf_embedded_text"],
            "trafilatura": available["article_extraction"],
        },
        "limits": {
            "max_upload_bytes": settings.max_upload_bytes,
            "max_text_chars": settings.max_text_chars,
            "max_pdf_pages": settings.max_pdf_pages,
            "max_claims": settings.max_claims,
        },
        "notes": [
            "Capabilities report local configuration, not provider authentication or network health.",
            "Only submitted content is processed; private WhatsApp chats cannot be read.",
        ],
    }


@router.post("/verify", response_model=VerificationResult)
async def verify(payload: VerifyRequest, request: Request):
    return await request.app.state.verifier.verify(payload)


@router.post("/extract", response_model=ExtractionResult)
async def extract(
    request: Request,
    file: Annotated[
        UploadFile,
        File(
            description="PNG/JPEG, PDF, WAV, MP3 or OGG/Opus. Format is detected from bytes, not the filename."
        ),
    ],
):
    try:
        data = await file.read(request.app.state.settings.max_upload_bytes + 1)
        return await request.app.state.media.extract(data)
    finally:
        await file.close()


@router.post("/extract/url", response_model=ExtractionResult)
async def extract_url(payload: URLRequest, request: Request):
    settings = request.app.state.settings
    fetched = await request.app.state.fetcher.fetch(payload.url)
    if fetched.content_type == "application/pdf":
        result = await request.app.state.media.extract(fetched.body)
        result.input_type = "url"
        result.extraction_details["url"] = fetched.url
        result.extraction_details["document_type"] = "pdf"
    elif fetched.content_type == "text/plain":
        decoded, encoding, lossy = decode_web_text(fetched.body, fetched.charset)
        text = normalize(decoded)
        if not text:
            raise AppError("url_no_text", "This page has no readable text.", 422)
        result = ExtractionResult(
            text=text,
            detected_language=detect_language(text),
            input_type="url",
            warnings=["text_encoding_loss: Some downloaded bytes could not be decoded."]
            if lossy
            else [],
            extraction_details={
                "url": fetched.url,
                "title": None,
                "published_at": None,
                "text_encoding": encoding,
                "content_complete": not lossy,
            },
        )
    else:
        result = await asyncio.to_thread(
            article_from_html, fetched.body, fetched.url, fetched.charset
        )
    result.extraction_details["source_url"] = payload.url
    if len(result.text) > settings.max_text_chars:
        result.extraction_details["full_text_chars"] = len(result.text)
        result.text = result.text[: settings.max_text_chars]
        result.warnings.append("extraction_text_truncated")
        result.extraction_details["content_complete"] = False
    if fetched.content_type != "application/pdf":
        result.extraction_details["chunks"] = [
            {
                "chunk_id": index + 1,
                "text": chunk.text,
                "start": chunk.start,
                "end": chunk.end,
                "boundary_split": chunk.boundary_split,
            }
            for index, chunk in enumerate(
                split_text(result.text, settings.document_chunk_chars, settings.max_document_chunks)
            )
        ]
        result.extraction_details["coverage"] = (
            "extracted_text_only"
            if "extraction_text_truncated" in result.warnings
            else "returned_article_text"
        )
    return result


@router.post("/explain", response_model=VerificationResult)
async def explain(payload: ExplainRequest, request: Request):
    return await reexplain(
        request.app.state.llm, payload.result, payload.language, payload.audience
    )
