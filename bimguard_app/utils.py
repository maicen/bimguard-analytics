import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fasthtml.common import RedirectResponse


def load_env_file(env_path: str = ".env") -> None:
    """Load local .env file into process environment without overriding set vars."""
    load_dotenv(dotenv_path=Path(env_path), override=False)


ALLOWED_DOCUMENT_SUFFIXES = {".pdf", ".md", ".txt"}
ALLOWED_DOCUMENT_MIME_BY_SUFFIX = {
    ".pdf": {"application/pdf"},
    ".md": {"text/markdown", "text/x-markdown", "text/plain"},
    ".txt": {"text/plain"},
}


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def md5_hex(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def safe_upload_name(filename: str | None) -> str:
    return Path(filename or "").name


def store_upload_bytes(filename: str, content: bytes, destination_dir: Path) -> Path:
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    stored_path = destination_dir / stored_name
    stored_path.write_bytes(content)
    return stored_path


def is_likely_text_content(content: bytes) -> bool:
    sample = content[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def validate_document_upload(
    filename: str,
    content_type: str | None,
    file_content: bytes,
) -> str | None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_SUFFIXES:
        return "Only PDF, Markdown (.md), and text (.txt) files are supported."

    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
    allowed_mime_types = ALLOWED_DOCUMENT_MIME_BY_SUFFIX.get(suffix, set())
    if normalized_content_type not in allowed_mime_types:
        return f"Invalid MIME type '{normalized_content_type or 'unknown'}' for {suffix} file."

    if not file_content:
        return "Uploaded file is empty."

    if suffix == ".pdf" and not file_content.startswith(b"%PDF-"):
        return "Uploaded file content does not match a valid PDF signature."

    if suffix in {".md", ".txt"} and not is_likely_text_content(file_content):
        return "Uploaded text/markdown file appears to be binary content."

    return None


def redirect_see_other(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def rows_desc_by_id(table) -> list[dict]:
    return sorted(list(table.rows), key=lambda row: row["id"], reverse=True)


def find_row_by_field(table, field_name: str, value):
    for row in table.rows:
        if row.get(field_name) == value:
            return row
    return None
