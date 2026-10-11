"""Create a separate private Sandbox config; never display/overwrite credentials."""

import argparse
import getpass
import re
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

from .config import Settings


def update_token(path, token):
    if not re.fullmatch(r"[0-9a-fA-F]{32}", token):
        raise ValueError("Copy the primary Auth Token from Twilio Account Info")
    if not Path(path).is_file():
        raise ValueError("Create the private configuration first")
    from dotenv import set_key

    set_key(str(path), "TWILIO_AUTH_TOKEN", token, quote_mode="always")


def write_config(path, account, token, number, public_url):
    if not re.fullmatch(r"[0-9a-fA-F]{32}", token):
        raise ValueError("Copy the primary Auth Token from Twilio Account Info")
    values = {
        "BOT_ENV": "test",
        "MESSAGING_PROVIDER": "twilio",
        "RESPONSE_MODE": "development",
        "TWILIO_OUTBOUND_ENABLED": "false",
        "META_OUTBOUND_ENABLED": "false",
        "BACKEND_ENABLED": "false",
        "PROVIDER_CREDENTIALS_ROTATED": "false",
        "TWILIO_ACCOUNT_SID": account,
        "TWILIO_AUTH_TOKEN": token,
        "TWILIO_WHATSAPP_NUMBER": number,
        "TWILIO_PUBLIC_BASE_URL": public_url.rstrip("/"),
        "STATE_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "IDENTITY_HASH_SECRET": secrets.token_urlsafe(32),
        "DATABASE_URL": "sqlite:///state/twilio-sandbox.sqlite3",
        "TRUTHLENS_BACKEND_URL": "http://127.0.0.1:8000",
    }
    if any("\n" in value or "\r" in value or "\x00" in value for value in values.values()):
        raise ValueError("Settings must each be a single line")
    # Validate without echoing validation input or secrets in a traceback.
    Settings(_env_file=None, **{key.lower(): value for key, value in values.items()})
    with Path(path).open("x", encoding="utf-8") as output:
        output.write("# Private Sandbox configuration. Never commit or share this file.\n")
        output.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Private Twilio Sandbox configuration")
    parser.add_argument(
        "--update-token", action="store_true", help="Replace only the Auth Token privately"
    )
    args = parser.parse_args()
    path = Path(".env.twilio")
    if args.update_token:
        token = getpass.getpass("Twilio primary Auth Token (hidden): ").strip()
        try:
            update_token(path, token)
        except (ValueError, OSError):
            print(
                "Token was not changed. Copy the 32-character primary Auth Token from Twilio Account Info; check that .env.twilio exists."
            )
            return
        print("Auth Token updated privately. Other settings and encryption keys were preserved.")
        return
    if path.exists():
        print(".env.twilio already exists. Preserved it; edit it privately in your editor.")
        return
    account = input("Twilio Account SID (starts with AC): ").strip()
    token = getpass.getpass("Twilio primary Auth Token (hidden): ").strip()
    number = input("Sandbox sender, exactly as shown (for example whatsapp:+14155238886): ").strip()
    public_url = input("HTTPS ngrok address, without a path: ").strip()
    try:
        write_config(path, account, token, number, public_url)
    except (ValueError, OSError):
        print(
            "Configuration was not created. Check the values privately; no credentials were printed."
        )
        return
    print(
        "Saved .env.twilio privately with live sending and AI disabled. Existing Meta .env is unchanged."
    )


if __name__ == "__main__":
    main()
