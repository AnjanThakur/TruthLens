import io
import json
import wave

import httpx
import pymupdf
import pytest
from conftest import StubFetcher, article
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from test_http_security import Resolver

from app.errors import AppError
from app.main import create_app
from app.services.extract.media import MediaExtractor, capabilities, ocr_image, pdf_extract
from app.services.extract.url import SafeFetcher, article_from_html


def pdf_bytes(scanned=None):
    document = pymupdf.open()
    first = document.new_page()
    if scanned:
        first.insert_image(pymupdf.Rect(20, 20, 580, 150), stream=scanned)
    else:
        first.insert_text((50, 70), "Page one: the library opens at 9 am. Embedded factual text.")
    second = document.new_page()
    second.insert_text(
        (50, 70), "Page two: the library remains open on Sundays. Embedded factual text."
    )
    result = document.tobytes()
    document.close()
    return result


def test_actual_embedded_text_multipage_pdf(settings):
    result = pdf_extract(pdf_bytes(), settings)
    assert "library opens" in result.text and "Sundays" in result.text
    assert result.extraction_details["processed_pages"] == 2
    assert [p["page_number"] for p in result.extraction_details["pages"]] == [1, 2]


def test_scanned_first_page_reports_ocr_availability(settings, screenshot):
    result = pdf_extract(pdf_bytes(screenshot), settings)
    first = result.extraction_details["pages"][0]
    if capabilities(settings)["ocr"]:
        assert first["method"] == "ocr" and "library" in first["text"].lower()
    else:
        assert first["method"] == "ocr_unavailable"
        assert any("ocr_unavailable" in warning for warning in result.warnings)
    assert "Sundays" in result.text


@pytest.mark.parametrize("format", ["PNG", "JPEG"])
def test_actual_ocr_when_runtime_available(settings, screenshot, format):
    if not capabilities(settings)["ocr"]:
        pytest.skip("Tesseract executable/language data absent; unavailable path tested separately")
    stream = io.BytesIO()
    Image.open(io.BytesIO(screenshot)).save(stream, format=format)
    text, details, _ = ocr_image(stream.getvalue(), settings)
    assert "library" in text.lower() and "9" in text
    assert details["ocr_confidence"] > 65


def test_ocr_unavailable_is_capability_error(settings, screenshot):
    settings.tesseract_cmd = "Z:/not-installed/tesseract.exe"
    with pytest.raises(AppError) as error:
        ocr_image(screenshot, settings)
    assert error.value.code == "ocr_unavailable"


def test_audio_unavailable_is_honest(settings):
    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 160)
    client = TestClient(create_app(settings))
    response = client.post(
        "/api/extract", files={"file": ("voice.wav", audio.getvalue(), "audio/wav")}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "transcription_unavailable"


@pytest.mark.parametrize(
    "transcript",
    ["The library opens at nine.", "पुस्तकालय सुबह नौ बजे खुलता है।", "वाचनालय सकाळी नऊ वाजता उघडते आहे."],
)
async def test_transcriber_http_contract_multilingual(settings, transcript):
    settings.gemini_api_key = SecretStr("test-only")

    async def handler(request):
        payload = json.loads(request.content)
        assert request.url.path.endswith("/interactions")
        assert payload["input"][0]["content"][0]["mime_type"] == "audio/wav"
        assert payload["input"][0]["content"][0]["data"]
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"text": transcript, "detected_language": "en"}),
                            }
                        ],
                    }
                ],
            },
        )

    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 160)
    result = await MediaExtractor(settings, httpx.MockTransport(handler)).extract(audio.getvalue())
    assert result.text == transcript
    assert result.input_type == "audio"


def test_html_actual_article_text_title_date(settings):
    text = "A new community library opened in the town on Friday. Its public reading rooms are available from nine in the morning. The town notice includes access details and opening hours for residents."
    result = article_from_html(
        article(text, title="Library opening", date="2026-01-15"), "https://public.test/news"
    )
    assert "community library" in result.text
    assert result.extraction_details["title"] == "Library opening"
    assert result.extraction_details["published_at"] == "2026-01-15"


def test_url_api_uses_extraction_common_contract(settings):
    client = TestClient(create_app(settings, fetcher=StubFetcher()))
    response = client.post("/api/extract/url", json={"url": "https://public.test/news"})
    assert response.status_code == 200, response.text
    assert {
        "text",
        "input_type",
        "warnings",
        "detected_language",
        "extraction_details",
    } <= response.json().keys()
    assert response.json()["input_type"] == "url"


def test_url_api_blocks_private(settings):
    fetcher = SafeFetcher(settings, Resolver({"internal.test": ["127.0.0.1"]}))
    client = TestClient(create_app(settings, fetcher=fetcher))
    response = client.post("/api/extract/url", json={"url": "http://internal.test/secret"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsafe_url"


def test_file_signature_not_filename_and_upload_limit(settings):
    settings.max_upload_bytes = 1024
    client = TestClient(create_app(settings))
    response = client.post(
        "/api/extract", files={"file": ("../../fake.pdf", b"This is not a PDF", "application/pdf")}
    )
    assert response.status_code == 415
    response = client.post("/api/extract", files={"file": ("big.png", b"a" * 1025, "image/png")})
    assert response.status_code == 413
    response = client.post("/api/extract", files={"file": ("empty.png", b"", "image/png")})
    assert response.status_code == 422


def test_corrupt_and_attachment_pdf_rejected(settings):
    with pytest.raises(AppError):
        pdf_extract(b"%PDF-invalid", settings)
    document = pymupdf.open()
    document.new_page()
    document.embfile_add("script.txt", b"untrusted")
    data = document.tobytes()
    document.close()
    with pytest.raises(AppError) as error:
        pdf_extract(data, settings)
    assert error.value.code == "unsafe_pdf"


def test_pdf_page_limit_is_visible(settings):
    settings.max_pdf_pages = 1
    result = pdf_extract(pdf_bytes(), settings)
    assert result.extraction_details["processed_pages"] == 1
    assert any("pdf_page_limit" in warning for warning in result.warnings)
