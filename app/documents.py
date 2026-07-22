from __future__ import annotations

import asyncio
import hashlib
import re
import threading
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
import pikepdf
from pikepdf import Array as PdfArray
from pikepdf import Dictionary as PdfDictionary
from pikepdf import Name as PdfName
from pikepdf import Stream as PdfStream


ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_DOCUMENTS_PER_CASE = 20
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 45 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
MAX_PDF_PAGES_PER_DOCUMENT = 100
MAX_TOTAL_PDF_PAGES_PER_CASE = 200
MAX_PDF_OBJECTS = 20_000
MAX_CONCURRENT_DOCUMENT_PROCESSORS = 2
_DOCUMENT_PROCESSING_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_DOCUMENT_PROCESSORS)


class DocumentValidationError(ValueError):
    """Raised when an uploaded document does not meet the safety rules."""


@dataclass(frozen=True)
class PreparedDocument:
    original_name: str
    content_type: str
    content: bytes
    size_bytes: int
    sha256: str
    page_count: int = 0


_FILENAME_RE = re.compile(r"[^\w.()\- ]+", re.UNICODE)


def safe_display_filename(raw_name: str | None, fallback: str = "document") -> str:
    name = Path(raw_name or fallback).name.replace("\x00", "").strip()
    name = _FILENAME_RE.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return (name or fallback)[:180]


def unique_display_filename(filename: str, used_names: set[str]) -> str:
    """Return a case-insensitively unique evidence filename for one case."""
    candidate = safe_display_filename(filename)
    if candidate.casefold() not in used_names:
        used_names.add(candidate.casefold())
        return candidate

    path = Path(candidate)
    suffix = path.suffix
    stem = path.stem or "document"
    index = 2
    while True:
        marker = f" ({index})"
        max_stem = max(1, 180 - len(suffix) - len(marker))
        renamed = f"{stem[:max_stem]}{marker}{suffix}"
        if renamed.casefold() not in used_names:
            used_names.add(renamed.casefold())
            return renamed
        index += 1


def detect_content_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _sanitise_image(data: bytes, detected_type: str) -> tuple[bytes, str]:
    try:
        with Image.open(BytesIO(data)) as image:
            # Check dimensions before decoding all pixels. This avoids unnecessary
            # memory use for compressed images with extreme dimensions.
            if image.width <= 0 or image.height <= 0 or image.width * image.height > MAX_IMAGE_PIXELS:
                raise DocumentValidationError("Image dimensions are not allowed")
            image.load()
            image = ImageOps.exif_transpose(image)
            output = BytesIO()
            if detected_type == "image/jpeg":
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                image.save(output, format="JPEG", quality=90, optimize=True)
            elif detected_type == "image/webp":
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                image.save(output, format="WEBP", quality=90, method=4)
            else:
                if image.mode not in {"RGB", "RGBA", "L", "LA"}:
                    image = image.convert("RGBA")
                image.save(output, format="PNG", optimize=True)
            cleaned = output.getvalue()
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise DocumentValidationError("The image is damaged or unsupported") from exc
    if not cleaned:
        raise DocumentValidationError("The image could not be processed")
    return cleaned, detected_type


def _decode_pdf_name_escapes(data: bytes) -> bytes:
    """Decode PDF name escapes such as /Java#53cript before safety checks."""
    return re.sub(
        rb"#([0-9A-Fa-f]{2})",
        lambda match: bytes([int(match.group(1), 16)]),
        data,
    )


_FORBIDDEN_PDF_NAMES = frozenset({
    "/javascript", "/js", "/launch", "/openaction", "/aa", "/gotoe",
    "/richmedia", "/xfa", "/embeddedfile", "/embeddedfiles", "/filespec",
    "/ef", "/af", "/afrelationship", "/collection", "/acroform",
    "/submitform", "/importdata", "/rendition", "/movie", "/sound",
})


def _pdf_name_is_forbidden(value: object) -> bool:
    return isinstance(value, PdfName) and str(value).casefold() in _FORBIDDEN_PDF_NAMES


def _inspect_direct_pdf_value(value: object, *, depth: int = 0) -> None:
    """Inspect direct child dictionaries/arrays without following indirect cycles."""
    if depth > 32:
        raise DocumentValidationError("The PDF structure is too deeply nested")
    if _pdf_name_is_forbidden(value):
        raise DocumentValidationError("PDFs containing active or embedded content are not accepted")
    if isinstance(value, (PdfDictionary, PdfStream)):
        for key, child in value.items():
            if str(key).casefold() in _FORBIDDEN_PDF_NAMES or _pdf_name_is_forbidden(child):
                raise DocumentValidationError("PDFs containing active or embedded content are not accepted")
            if getattr(child, "is_indirect", False):
                continue
            _inspect_direct_pdf_value(child, depth=depth + 1)
    elif isinstance(value, PdfArray):
        for child in value:
            if getattr(child, "is_indirect", False):
                continue
            _inspect_direct_pdf_value(child, depth=depth + 1)


def validate_pdf_and_count_pages(data: bytes) -> tuple[bytes, int]:
    if not data.startswith(b"%PDF-"):
        raise DocumentValidationError("The PDF signature is invalid")
    # Reject obvious polyglot or truncated uploads before invoking the parser.
    if b"%%EOF" not in data[-4096:]:
        raise DocumentValidationError("The PDF appears incomplete")

    try:
        with pikepdf.Pdf.open(BytesIO(data), suppress_warnings=True) as pdf:
            if pdf.is_encrypted:
                raise DocumentValidationError("Password-protected PDFs are not accepted")
            if len(pdf.objects) > MAX_PDF_OBJECTS:
                raise DocumentValidationError("The PDF contains too many internal objects")
            page_count = len(pdf.pages)
            if page_count <= 0:
                raise DocumentValidationError("The PDF contains no pages")
            if page_count > MAX_PDF_PAGES_PER_DOCUMENT:
                raise DocumentValidationError(
                    f"Each PDF can contain no more than {MAX_PDF_PAGES_PER_DOCUMENT} pages"
                )

            # pikepdf expands compressed object streams before exposing objects.
            # This closes the v3.6.7 gap where /EmbeddedFiles or /Filespec could
            # be hidden inside /ObjStm and evade a raw-byte regular expression.
            for pdf_object in pdf.objects:
                if isinstance(pdf_object, (PdfDictionary, PdfStream)):
                    for key, value in pdf_object.items():
                        if str(key).casefold() in _FORBIDDEN_PDF_NAMES or _pdf_name_is_forbidden(value):
                            raise DocumentValidationError(
                                "PDFs containing active or embedded content are not accepted"
                            )
                        if not getattr(value, "is_indirect", False):
                            _inspect_direct_pdf_value(value)
    except DocumentValidationError:
        raise
    except pikepdf.PasswordError as exc:
        raise DocumentValidationError("Password-protected PDFs are not accepted") from exc
    except (pikepdf.PdfError, ValueError, OverflowError, MemoryError) as exc:
        raise DocumentValidationError("The PDF is damaged, unsafe or unsupported") from exc
    return data, page_count


def _validate_pdf(data: bytes) -> bytes:
    """Backward-compatible wrapper retained for scripts and existing tests."""
    return validate_pdf_and_count_pages(data)[0]


def _process_document_bytes_unbounded(raw: bytes, detected: str) -> tuple[bytes, str, int]:
    if detected in IMAGE_CONTENT_TYPES:
        content, content_type = _sanitise_image(raw, detected)
        return content, content_type, 0
    content, page_count = validate_pdf_and_count_pages(raw)
    return content, detected, page_count


def _process_document_bytes(raw: bytes, detected: str) -> tuple[bytes, str, int]:
    """Perform CPU-heavy validation in a globally bounded worker section."""
    # A 30-megapixel decoded image can occupy well over 100 MB. Bounding the
    # number of concurrent decoders prevents several simultaneous uploads from
    # exhausting a small Render instance after work is moved off the event loop.
    with _DOCUMENT_PROCESSING_SLOTS:
        return _process_document_bytes_unbounded(raw, detected)


async def prepare_upload(upload: UploadFile) -> PreparedDocument:
    raw = await upload.read(MAX_DOCUMENT_BYTES + 1)
    await upload.close()
    if not raw:
        raise DocumentValidationError("The selected file is empty")
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise DocumentValidationError("Each file must be 8 MB or smaller")

    detected = detect_content_type(raw)
    if detected not in ALLOWED_CONTENT_TYPES:
        raise DocumentValidationError("Only PDF, JPG, PNG and WebP files are accepted")

    # Re-encoding a 20–30 megapixel image can take close to a second. Running
    # that work directly in this async route would pause every request handled
    # by the same Uvicorn worker. Keep the operation sequential to bound memory,
    # but move each file's CPU work to Starlette/Python's worker thread pool.
    processed = await asyncio.to_thread(_process_document_bytes, raw, detected)
    # Keep test/custom processors written for the pre-page-count interface compatible.
    if len(processed) == 2:
        content, final_type = processed
        page_count = 0
    else:
        content, final_type, page_count = processed

    if len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentValidationError("The processed file is larger than 8 MB")

    extension = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[final_type]
    original_name = safe_display_filename(upload.filename)
    if not original_name.lower().endswith(extension):
        original_name = f"{Path(original_name).stem or 'document'}{extension}"

    return PreparedDocument(
        original_name=original_name,
        content_type=final_type,
        content=content,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        page_count=page_count,
    )
