"""Generate a public click-to-chat QR only after the owner verifies the real number."""

import argparse
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--number", required=True, help="Verified public number, country code, digits only"
    )
    parser.add_argument("--output", default="state/whatsapp-qr.svg")
    parser.add_argument("--number-verified", action="store_true")
    args = parser.parse_args()
    if not args.number_verified or not re.fullmatch(r"[1-9]\d{6,14}", args.number):
        parser.error("Use a verified actual public number and --number-verified")
    import qrcode
    import qrcode.image.svg

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = qrcode.make(f"https://wa.me/{args.number}", image_factory=qrcode.image.svg.SvgPathImage)
    image.save(output)
    print(
        "QR saved locally. Test it before publication; creating a QR does not prove messaging works."
    )


if __name__ == "__main__":
    main()
