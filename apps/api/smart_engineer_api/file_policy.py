"""File policy for project attachments (FILE-001, SEC-002).

All limits are Phase 1 development defaults pending DEC-023 (owner-delegated,
assistant-proposed). The type is decided from the file's own bytes, never from the
client-supplied name or content type, and the extension must agree with it.

The built-in scanner is NOT an antivirus: it rejects the EICAR test signature and
PDFs carrying active content markers. Production must plug in a real scanner (a
DEC-023 decision); until then ``clean`` is only granted outside production.
"""

import re
from dataclasses import dataclass

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB per file
MAX_FILES_PER_PROJECT = 100
MAX_NAME_LENGTH = 200

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}
EXTENSIONS = {
    "pdf": (".pdf",),
    "png": (".png",),
    "jpeg": (".jpg", ".jpeg"),
    "webp": (".webp",),
}

EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_PDF_ACTIVE_MARKERS = (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def detect_type(content: bytes) -> str | None:
    """Return one of CONTENT_TYPES' keys from the leading bytes, or None."""
    if content.startswith(b"%PDF-"):
        return "pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


def clean_filename(raw: str) -> str | None:
    """Keep only a safe display name (no path parts, no control characters)."""
    name = _CONTROL.sub("", raw.replace("\\", "/").split("/")[-1]).strip().strip(".")
    if not name or len(name) > MAX_NAME_LENGTH:
        return None
    return name


def extension_matches(name: str, detected: str) -> bool:
    return name.lower().endswith(EXTENSIONS[detected])


@dataclass(frozen=True, slots=True)
class ScanResult:
    verdict: str  # "clean" or "quarantined"
    detail: str | None = None


def builtin_scan(content: bytes, detected: str) -> ScanResult:
    if EICAR_SIGNATURE in content:
        return ScanResult("quarantined", "eicar_test_signature")
    if detected == "pdf" and any(marker in content for marker in _PDF_ACTIVE_MARKERS):
        return ScanResult("quarantined", "pdf_active_content")
    return ScanResult("clean")
