import re
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

from .errors import ServiceError
from .formatter import DEVELOPMENT, format_reports

LANGUAGES = {"HINDI": "hi", "MARATHI": "mr", "ENGLISH": "en"}


class MessageHandler:
    def __init__(self, settings, store, meta, backend):
        self.settings, self.store, self.meta, self.backend = settings, store, meta, backend

    async def handle(self, job):
        message = self.store.open(job["payload"])
        if time.time() - int(message["timestamp"]) > 86400:
            raise ServiceError("window_expired")
        sender = job["sender"]
        text = message.get("text", {}).get("body", "").strip()
        command = text.upper()
        if command == "STOP":
            return [
                "TruthLens: stopped. Pending replies are suppressed. Send START to request checks again."
            ], None
        if command == "START":
            return [
                "TruthLens: ready for your requested checks. Send HELP for privacy and supported formats."
            ], None
        if self.store.preference(sender)["stopped"]:
            return [], None
        if command == "HELP":
            return [
                "TruthLens checks content you choose to send: text, JPEG/PNG, supported audio, PDF or one public URL. Only submitted messages are processed. Processing content expires within 24 hours; it is not saved to website history. Do not send sensitive personal documents. "
                + (
                    f"Support: {self.settings.support_url}. "
                    if self.settings.support_url
                    else "Use the project website for help; live support is not configured. "
                )
                + "HINDI | MARATHI | ENGLISH | SOURCES | STOP"
            ], None
        language = self.store.preference(sender)["language"]
        if command in LANGUAGES and self.settings.response_mode == "development":
            self.store.preference(sender, LANGUAGES[command])
            return [
                "Preference updated. Development connectivity mode does not perform fact checks."
            ], None
        if command == "SOURCES" and self.settings.response_mode == "development":
            return [
                "Development connectivity mode has no fact-check sources. Use the website for a check."
            ], None
        if self.settings.response_mode == "development":
            return [DEVELOPMENT], None
        if command in LANGUAGES or command == "SOURCES":
            if command in LANGUAGES:
                language = LANGUAGES[command]
                self.store.preference(sender, language)
            saved = self.store.last_report(sender)
            if not saved:
                return [
                    "Preference updated. Send content to check; there is no recent report to display."
                ], None
            reports = saved["reports"]
            if command != "SOURCES":
                reports = [await self.backend.explain(report, language) for report in reports]
            return format_reports(
                reports, extraction_warnings=saved["warnings"], sources_only=command == "SOURCES"
            ), {"reports": reports, "warnings": saved["warnings"]}
        kind, warnings = message["type"], []
        extracted = None
        if kind == "text":
            urls = re.findall(r"https?://\S+", text)
            if urls:
                if len(urls) != 1 or text != urls[0]:
                    return [
                        "Please send one public article URL by itself, or paste the claim text separately."
                    ], None
                parsed = urlsplit(text)
                if parsed.username or parsed.password:
                    raise ServiceError("unsafe_url")
                extracted = await self.backend.extract_url(text)
                kind = "url"
        elif kind in {"image", "audio", "document"}:
            media = message[kind]
            if kind == "document" and media.get("mime_type") != "application/pdf":
                raise ServiceError("unsupported_media")
            data, mime = await self.meta.media(media["id"], kind)
            extracted = await self.backend.extract(data, mime)
            kind = {"image": "image", "audio": "audio", "document": "pdf"}[kind]
            if extracted["input_type"] != kind:
                raise ServiceError("backend_contract")
        else:
            return [
                "Please send text, a JPEG/PNG screenshot, supported voice/audio, a PDF, or one public article URL."
            ], None
        if extracted:
            text = extracted["text"]
            warnings = list(extracted["warnings"])
            details = extracted["extraction_details"]
            if details.get("text_is_preview"):
                # Avoid silently verifying a preview or unexpectedly spending many model calls.
                return [
                    "This document exceeds a single check. Please split it into smaller PDFs or use the website to review its page chunks. No whole-document verdict was generated."
                ], None
            if details.get("content_complete") is False:
                warnings.append(
                    "Only returned article text was available; this does not check the whole article."
                )
        if not text.strip():
            raise ServiceError("extraction_empty")
        result = await self.backend.verify(
            text,
            kind,
            language,
            message_time=datetime.fromtimestamp(int(message["timestamp"]), UTC).isoformat(),
        )
        return format_reports([result], extraction_warnings=warnings), {
            "reports": [result],
            "warnings": warnings,
        }
