"""Generate real media containing DEMO CLAIMS, never synthetic web evidence."""

from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

TEXT = "From Monday all Rs 500 notes are invalid.\nRBI publishes currency notices.\nForward to everyone immediately!"


def main():
    target = Path(__file__).resolve().parents[1] / "demo-output" / "fixtures"
    target.mkdir(parents=True, exist_ok=True)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 38)
    except OSError:
        font = ImageFont.load_default(size=38)
    image = Image.new("RGB", (1300, 260), "white")
    ImageDraw.Draw(image).multiline_text((25, 35), TEXT, fill="black", font=font, spacing=18)
    image.save(target / "forward.png")
    image.save(target / "forward.jpg", quality=95)
    (target / "forward.txt").write_text(TEXT, encoding="utf-8")
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 70), "From Monday all Rs 500 notes are invalid.", fontsize=15)
    page = document.new_page()
    page.insert_text((50, 70), "RBI publishes currency notices. Forward to everyone!", fontsize=15)
    document.save(target / "forward.pdf")
    document.close()
    samples = {
        "banknote": "All Rs 500 notes will become invalid next Monday.",
        "banknote-hi": "अगले सोमवार सभी 500 रुपये के नोट अमान्य हो जाएंगे।",
        "banknote-mr": "पुढील सोमवारी सर्व 500 रुपयांच्या नोटा अवैध होतील.",
    }
    for name, text in samples.items():
        font_path = (
            "C:/Windows/Fonts/arial.ttf" if name == "banknote" else "C:/Windows/Fonts/Nirmala.ttc"
        )
        try:
            sample_font = ImageFont.truetype(font_path, 48)
        except OSError:
            print(f"SKIPPED {name}: required font is unavailable.")
            continue
        sample = Image.new("RGB", (1800, 200), "white")
        ImageDraw.Draw(sample).text((30, 50), text, font=sample_font, fill="black")
        sample.save(target / (name + ".png"))
    document = pymupdf.open()
    page = document.new_page()
    page.insert_image(pymupdf.Rect(20, 20, 580, 95), filename=str(target / "banknote.png"))
    document.save(target / "banknote-scanned.pdf")
    document.close()
    document = pymupdf.open()
    page = document.new_page()
    page.insert_image(pymupdf.Rect(20, 20, 580, 150), filename=str(target / "forward.png"))
    page = document.new_page()
    page.insert_text((50, 70), "RBI publishes currency notices. Forward to everyone!", fontsize=15)
    document.save(target / "scanned-first.pdf")
    document.close()
    print(f"Demo input fixtures written to {target}. These are prompts, not fact-check results.")


if __name__ == "__main__":
    main()
