import os
import shutil
from pathlib import Path

from app.config import Settings


def executable(name: str, configured: str = "") -> str | None:
    if configured:
        return configured if Path(configured).is_file() else None
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        if name == "tesseract":
            candidate = (
                Path(os.environ.get("ProgramFiles", "C:/Program Files"))
                / "Tesseract-OCR"
                / "tesseract.exe"
            )
            if candidate.is_file():
                return str(candidate)
        if name in {"ffmpeg", "ffprobe"}:
            base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
            candidates = sorted(base.glob(f"Gyan.FFmpeg_*/*/bin/{name}.exe"))
            if candidates:
                return str(candidates[-1])
    return None


def tessdata(settings: Settings) -> str | None:
    if settings.tessdata_dir:
        return settings.tessdata_dir
    local = Path(__file__).resolve().parents[3] / ".runtime" / "tessdata"
    return str(local) if local.is_dir() else None
