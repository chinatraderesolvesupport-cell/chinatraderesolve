from __future__ import annotations

import hashlib
import re
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
            image.load()
            if image.width <= 0 or image.height <= 0 or image.width * image.height > MAX_IMAGE_PIXELS:
                raise DocumentValidationError("Image dimensions are not allowed")
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
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise DocumentValidationError("The image is damaged or unsupported") from exc
    if not cleaned:
        raise DocumentValidationError("The image could not be processed")
    return cleaned, detected_type


def _validate_pdf(data: bytes) -> bytes:
    if not data.startswith(b"%PDF-"):
        raise DocumentValidationError("The PDF signature is invalid")
    # Reject obvious polyglot or truncated uploads while keeping validation dependency-free.
    if b"%%EOF" not in data[-4096:]:
        raise DocumentValidationError("The PDF appears incomplete")
    if b"/JavaScript" in data or b"/JS" in data or b"/Launch" in data:
        raise DocumentValidationError("PDFs containing active content are not accepted")
    return data


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

    if detected in IMAGE_CONTENT_TYPES:
        content, final_type = _sanitise_image(raw, detected)
    else:
        content, final_type = _validate_pdf(raw), detected

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
