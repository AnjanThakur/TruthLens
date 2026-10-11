"""Package current project source, excluding private and generated material.

Uses only the standard library and local Git reads. No network or account access.
Run from any directory: py -3.12 scripts/build_handoff.py
"""

import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "handoff" / "TruthLens-Friend-Handoff.zip"
TREES = {
    ".github", "backend", "docs", "frontend", "supabase",
    "whatsapp-adapter", "TruthLens_Person2_Codex_Package", "scripts",
}
ROOT_FILES = {
    ".gitignore", "README.md", "START-HERE.md", "FRIEND-MESSAGE.txt",
    "TruthLens_Person2_WhatsApp_Bot_Integration_Guide.docx",
    "TruthLens_Person2_WhatsApp_Codex_Prompt.md",
}
BLOCKED_PARTS = {
    ".git", ".tmp", ".runtime", ".venv", "venv", "node_modules", ".next",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__", "state",
    "test-results", "playwright-report", "coverage", "dist", "out", ".vercel",
    "demo-output", "qa",
}
EXTENSIONS = {
    ".py", ".ts", ".tsx", ".mjs", ".json", ".css", ".svg", ".md",
    ".sql", ".yml", ".yaml", ".toml", ".txt", ".docx",
}
SPECIAL_NAMES = {
    ".env.example", ".gitignore", ".dockerignore", ".prettierignore", "Dockerfile",
}
REQUIRED = {
    "START-HERE.md", "FRIEND-MESSAGE.txt", "docs/current-integration-handoff.md",
    "docs/person2-local-acceptance.md", "docs/backend-openapi.json",
    "docs/backend-api-contract.md", "docs/person2-contract-reconciliation.md",
    "docs/twilio-sandbox-setup.md", "backend/.env.example", "backend/app/main.py",
    "frontend/.env.example", "frontend/package-lock.json",
    "frontend/tests/fixtures/person1-response.json",
    "whatsapp-adapter/.env.example", "whatsapp-adapter/requirements-twilio-lock.txt",
    "whatsapp-adapter/truthlens_whatsapp/configure_twilio.py",
    "whatsapp-adapter/truthlens_whatsapp/controlled_test.py",
    "supabase/migrations/202610110001_private_reports.sql",
    "supabase/migrations/202610110002_retention.sql",
    "TruthLens_Person2_Codex_Package/TruthLens_PS_Aligned_Two_Developer_Plan.docx",
    ".github/workflows/person2-offline.yml", "scripts/build_handoff.py",
}
COMMON_KEY = re.compile(
    rb"AIza[0-9A-Za-z_-]{30,}|tvly-[0-9A-Za-z_-]{25,}|"
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def shareable(name):
    if not name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        return False
    if len(path.parts) == 1:
        return name in ROOT_FILES
    if path.parts[0] not in TREES:
        return False
    if any(part in BLOCKED_PARTS or part.endswith(".egg-info") for part in path.parts):
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    if path.suffix in {".tsbuildinfo", ".log", ".db", ".sqlite", ".sqlite3"}:
        return False
    return path.name in SPECIAL_NAMES or path.suffix in EXTENSIONS


def private_values():
    """Read known local secret values privately, solely to refuse their inclusion."""
    values = set()
    for folder in (ROOT, ROOT / "backend", ROOT / "frontend", ROOT / "whatsapp-adapter"):
        for path in folder.glob(".env*"):
            if not path.is_file() or path.name == ".env.example":
                continue
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                match = re.match(r"(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)", line.strip())
                if not match:
                    continue
                key, value = match.groups()
                if not re.search(r"(?:API_KEY|TOKEN|SECRET|ENCRYPTION_KEY|PASSWORD)$", key):
                    continue
                value = value.strip().strip("\"'")
                if len(value) >= 12:
                    values.add(value.encode())
    return values


def inspect_content(name, data, secrets):
    chunks = [data]
    if name.endswith(".docx"):
        with zipfile.ZipFile(BytesIO(data)) as document:
            chunks.extend(document.read(item) for item in document.namelist())
    for chunk in chunks:
        if COMMON_KEY.search(chunk) or any(value in chunk for value in secrets):
            raise ValueError(f"Possible credential in {name}; packaging stopped (value withheld)")


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive CRC check failed")
        manifest = json.loads(archive.read("TruthLens/HANDOFF-MANIFEST.json"))
        expected = {"TruthLens/HANDOFF-MANIFEST.json"}
        expected.update("TruthLens/" + item["path"] for item in manifest["files"])
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
            raise ValueError("Archive manifest membership mismatch")
        included = set()
        for item in manifest["files"]:
            name = item["path"]
            if not shareable(name):
                raise ValueError(f"Disallowed archive path: {name}")
            data = archive.read("TruthLens/" + name)
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"Archive file hash mismatch: {name}")
            included.add(name)
        missing = REQUIRED - included
        if missing:
            raise ValueError("Required files missing: " + ", ".join(sorted(missing)))
        return manifest


def main():
    if sys.argv[1:] == ["--verify"]:
        manifest = verify_archive(OUTPUT)
        print(f"Verified {len(manifest['files'])} files; CRC, manifest, hashes and path exclusions passed.")
        return
    if len(sys.argv) > 1:
        raise ValueError("Usage: build_handoff.py [--verify]")
    candidates = set(git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0"))
    secrets = private_values()
    files = []
    for name in sorted(filter(shareable, candidates)):
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or ROOT not in path.resolve().parents:
            raise ValueError(f"Source path missing or unsafe: {name}")
        if any(parent.is_symlink() for parent in path.parents if parent != ROOT):
            raise ValueError(f"Source symlink refused: {name}")
        data = path.read_bytes()
        inspect_content(name, data, secrets)
        files.append((name, data))
    if REQUIRED - {name for name, _ in files}:
        raise ValueError("Required source missing; no handoff was built")
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "https://github.com/AnjanThakur/TruthLens",
        "branch": git("branch", "--show-current").decode().strip(),
        "base_commit": git("rev-parse", "HEAD").decode().strip(),
        "snapshot": "Current working files, including uncommitted changes; no Git history included.",
        "excluded": "Private env, screenshots, chat state, caches, dependencies, generated artifacts and Git history.",
        "credential_check": "Known local env secret values and common key/private-key patterns checked, including DOCX contents. Not a comprehensive secret audit.",
        "files": [
            {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in files
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT.with_suffix(".zip.pending")
    try:
        with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files:
                archive.writestr("TruthLens/" + name, data)
            archive.writestr("TruthLens/HANDOFF-MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
        verify_archive(pending)
        pending.replace(OUTPUT)
    finally:
        pending.unlink(missing_ok=True)
    print(f"Built {OUTPUT}")
    print(f"Verified {len(files)} source/config/document files; {OUTPUT.stat().st_size:,} bytes.")
    print("Known private-value/common-key checks, DOCX content checks, exclusions, CRC and hashes passed.")
    print("Private credentials and Git history were not packaged. No account/network actions performed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        # Avoid printing subprocess output, configuration values or arbitrary tracebacks.
        if isinstance(error, ValueError):
            print(str(error), file=sys.stderr)
        else:
            print("Handoff could not be built/verified; check local paths and Git availability.", file=sys.stderr)
        sys.exit(1)
