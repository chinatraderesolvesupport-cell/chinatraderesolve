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


ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_DOCUMENTS_PER_CASE = 20
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 45 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
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


def _validate_pdf(data: bytes) -> bytes:
    if not data.startswith(b"%PDF-"):
        raise DocumentValidationError("The PDF signature is invalid")
    # Reject obvious polyglot or truncated uploads while keeping validation dependency-free.
    if b"%%EOF" not in data[-4096:]:
        raise DocumentValidationError("The PDF appears incomplete")

    normalised = _decode_pdf_name_escapes(data)
    if re.search(rb"/(Encrypt)\b", normalised, flags=re.IGNORECASE):
        raise DocumentValidationError("Password-protected PDFs are not accepted")
    active_names = (
        rb"/(JavaScript|JS|Launch|OpenAction|AA|EmbeddedFile|RichMedia|XFA)\b"
    )
    if re.search(active_names, normalised, flags=re.IGNORECASE):
        raise DocumentValidationError("PDFs containing active or embedded content are not accepted")
    return data


def _process_document_bytes_unbounded(raw: bytes, detected: str) -> tuple[bytes, str]:
    if detected in IMAGE_CONTENT_TYPES:
        return _sanitise_image(raw, detected)
    return _validate_pdf(raw), detected


def _process_document_bytes(raw: bytes, detected: str) -> tuple[bytes, str]:
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
    content, final_type = await asyncio.to_thread(_process_document_bytes, raw, detected)

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
    )
