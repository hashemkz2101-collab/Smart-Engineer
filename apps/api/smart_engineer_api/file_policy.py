"""File policy for project attachments (FILE-001, SEC-002).

All limits are Phase 1 development defaults pending DEC-023 (owner-delegated,
assistant-proposed). The type is decided from the file's own bytes, never from the
client-supplied name or content type, and the extension must agree with it.

The built-in scanner is NOT an antivirus: it rejects the EICAR test signature and
PDFs carrying active content markers. Production must plug in a real scanner (a
DEC-023 decision); until then ``clean`` is only granted outside production.
"""

import io
import re
import zipfile
from dataclasses import dataclass

MIB = 1024 * 1024
MAX_FILES_PER_PROJECT = 100
MAX_NAME_LENGTH = 200

# Allowed formats (DEC-023, owner-approved 2026-11-24). Macro-enabled Office files
# (DOCM, XLSM, ...) are deliberately not allowed for now.
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "dxf": "image/vnd.dxf",
    "dwg": "image/vnd.dwg",
    "ifc": "application/x-step",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}
EXTENSIONS = {
    "pdf": (".pdf",),
    "png": (".png",),
    "jpeg": (".jpg", ".jpeg"),
    "webp": (".webp",),
    "dxf": (".dxf",),
    "dwg": (".dwg",),
    "ifc": (".ifc",),
    "xlsx": (".xlsx",),
    "xls": (".xls",),
    "csv": (".csv",),
    "docx": (".docx",),
    "doc": (".doc",),
}
# Per-type size limits: development defaults. CAD and BIM models are large, but a
# whole upload is held in memory, so the ceiling stays modest until streaming storage.
MAX_BYTES_BY_TYPE = {
    "pdf": 25 * MIB,
    "png": 10 * MIB,
    "jpeg": 10 * MIB,
    "webp": 10 * MIB,
    "dxf": 50 * MIB,
    "dwg": 50 * MIB,
    "ifc": 50 * MIB,
    "xlsx": 25 * MIB,
    "xls": 25 * MIB,
    "csv": 25 * MIB,
    "docx": 25 * MIB,
    "doc": 25 * MIB,
}
MAX_UPLOAD_BYTES = max(MAX_BYTES_BY_TYPE.values())

# Archive guards for OOXML (DOCX/XLSX are ZIP files).
MAX_ARCHIVE_ENTRIES = 5000
MAX_ARCHIVE_UNCOMPRESSED = 500 * MIB
_MAX_PART_READ = MIB

EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_PDF_ACTIVE_MARKERS = (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True, slots=True)
class Classification:
    """The detected type, or why a recognizable file is refused."""

    type: str | None
    reason: str | None = None  # "macro_not_allowed" or "unsafe_archive"


_DWG = re.compile(rb"^AC(?:1\.[0-9]{2}|2\.[0-9]{2}|10[0-3][0-9])")
_DXF = re.compile(
    r"^\s*(?:999\r?\n[^\r\n]*\r?\n\s*)*0\r?\nSECTION\r?\n\s*2\r?\n"
    r"(?:HEADER|CLASSES|TABLES|BLOCKS|ENTITIES|OBJECTS)\b"
)
_IFC_SCHEMA = re.compile(rb"FILE_SCHEMA\s*\(\s*\(\s*'IFC", re.IGNORECASE)
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_CSV_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-le")


_OLE_MACRO_MARKERS = (_utf16("_VBA_PROJECT"), _utf16("VBA"), _utf16("Macros"))


def _classify_zip(content: bytes) -> Classification:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        return Classification(None)
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES or sum(i.file_size for i in infos) > MAX_ARCHIVE_UNCOMPRESSED:
            return Classification(None, "unsafe_archive")
        names = [i.filename for i in infos]
        for name in names:
            parts = name.split("/")
            if name.startswith("/") or "\\" in name or ".." in parts or "\x00" in name:
                return Classification(None, "unsafe_archive")
        lowered = {name.lower() for name in names}
        if "[content_types].xml" not in lowered:
            return Classification(None)
        if any(name.endswith("vbaproject.bin") or "/vbadata" in name for name in lowered):
            return Classification(None, "macro_not_allowed")
        try:
            types_xml = archive.read("[Content_Types].xml")[:_MAX_PART_READ].lower()
        except (KeyError, zipfile.BadZipFile, RuntimeError):
            return Classification(None)
        if b"macroenabled" in types_xml or b"vnd.ms-office.vbaproject" in types_xml:
            return Classification(None, "macro_not_allowed")
        if "word/document.xml" in lowered:
            return Classification("docx")
        if "xl/workbook.xml" in lowered:
            return Classification("xlsx")
    return Classification(None)


def _classify_ole(content: bytes) -> Classification:
    if any(marker in content for marker in _OLE_MACRO_MARKERS):
        return Classification(None, "macro_not_allowed")
    if _utf16("WordDocument") in content:
        return Classification("doc")
    if _utf16("Workbook") in content or _utf16("Book") in content:
        return Classification("xls")
    return Classification(None)


def _classify_text(content: bytes) -> Classification:
    head = content[:8192]
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped.startswith(b"ISO-10303-21;") and _IFC_SCHEMA.search(head):
        return Classification("ifc")
    if content.startswith(b"AutoCAD Binary DXF\r\n\x1a\x00"):
        return Classification("dxf")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return Classification(None)
    if _CSV_CONTROL.search(text):
        return Classification(None)
    if _DXF.match(text[:4096]):
        return Classification("dxf")
    first_line = text.split("\n", 1)[0]
    if any(delimiter in first_line for delimiter in (",", ";", "\t")):
        return Classification("csv")
    return Classification(None)


def classify(content: bytes) -> Classification:
    """Decide the type from the file's own bytes; refuse macros and unsafe archives."""
    if content.startswith(b"%PDF-"):
        return Classification("pdf")
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return Classification("png")
    if content.startswith(b"\xff\xd8\xff"):
        return Classification("jpeg")
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return Classification("webp")
    if _DWG.match(content):
        return Classification("dwg")
    if content.startswith(b"PK\x03\x04"):
        return _classify_zip(content)
    if content.startswith(_OLE_MAGIC):
        return _classify_ole(content)
    return _classify_text(content)


def detect_type(content: bytes) -> str | None:
    """Return one of CONTENT_TYPES' keys from the file's bytes, or None."""
    return classify(content).type


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
    if detected in ("docx", "xlsx"):
        problem = _ooxml_active_content(content)
        if problem:
            return ScanResult("quarantined", problem)
    return ScanResult("clean")


_EXTERNAL_RELATIONSHIP = re.compile(rb'TargetMode\s*=\s*"External"', re.IGNORECASE)
_RISKY_EXTERNAL = (b"attachedtemplate", b"oleobject", b"frame", b"subdocument", b"externallink")


def _ooxml_active_content(content: bytes) -> str | None:
    """Embedded objects, ActiveX and links to outside templates or workbooks."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        return "ooxml_unreadable"
    with archive:
        for info in archive.infolist():
            name = info.filename.lower()
            if "/embeddings/" in name or "/activex/" in name or name.startswith("activex/"):
                return "office_embedded_object"
        for info in archive.infolist()[:MAX_ARCHIVE_ENTRIES]:
            if not info.filename.lower().endswith(".rels"):
                continue
            try:
                data = archive.read(info)[:_MAX_PART_READ]
            except (zipfile.BadZipFile, RuntimeError):
                return "ooxml_unreadable"
            if _EXTERNAL_RELATIONSHIP.search(data) and any(
                token in data.lower() for token in _RISKY_EXTERNAL
            ):
                return "office_external_link"
    return None
