import io
import subprocess
import tempfile
import wave
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.errors import AppError
from app.services.common import detect_language
from app.services.extract.media import audio_duration, capabilities, convert_ogg, ocr_image
from app.services.extract.runtime import executable


@pytest.mark.parametrize(
    "language,text",
    [
        ("hi", "अगले सोमवार सभी 500 रुपये के नोट अमान्य हो जाएंगे।"),
        ("mr", "पुढील सोमवारी सर्व 500 रुपयांच्या नोटा अवैध होतील."),
    ],
)
def test_real_devanagari_ocr_and_language(settings, language, text):
    if not capabilities(settings)["ocr"]:
        pytest.skip("Tesseract is not installed")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/Nirmala.ttc", 48)
    except OSError:
        pytest.skip("Devanagari font is not installed")
    image = Image.new("RGB", (1800, 200), "white")
    ImageDraw.Draw(image).text((30, 50), text, font=font, fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    extracted, _, _ = ocr_image(buffer.getvalue(), settings)
    assert "500" in extracted
    assert "अमान्य" in extracted or "अवैध" in extracted
    assert detect_language(extracted) == language


@pytest.mark.parametrize("kind,codec", [("mp3", "libmp3lame"), ("ogg", "libopus")])
def test_real_ffmpeg_ffprobe_and_ogg_conversion(settings, kind, codec):
    ffmpeg = executable("ffmpeg", settings.ffmpeg_cmd)
    if not ffmpeg or not executable("ffprobe", settings.ffprobe_cmd):
        pytest.skip("FFmpeg/FFprobe are not installed")
    with tempfile.TemporaryDirectory(prefix="truthlens-native-test-") as folder:
        source = Path(folder) / "source.wav"
        with wave.open(str(source), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0\0" * 16000)
        target = source.with_suffix("." + kind)
        completed = subprocess.run(  # noqa: S603 - fixed codec, configured executable, generated paths.
            [ffmpeg, "-v", "error", "-nostdin", "-i", str(source), "-c:a", codec, str(target)],
            capture_output=True,
            check=False,
            timeout=20,
        )  # noqa: S603
        assert completed.returncode == 0
        data = target.read_bytes()
        assert 0.9 <= audio_duration(data, kind, settings) <= 1.2
        if kind == "ogg":
            assert 0.9 <= audio_duration(convert_ogg(data, settings), "wav", settings) <= 1.2


def test_truncated_wav_frames_rejected(settings):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 1000)
    with pytest.raises(AppError) as error:
        audio_duration(buffer.getvalue()[:-200], "wav", settings)
    assert error.value.code == "invalid_audio"
