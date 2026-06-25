"""
File text extraction service.

Supports the two formats called out in the product spec: plain TXT and PDF.
PDF parsing happens server-side with pypdf since client-side extraction is
unreliable across the wide variety of PDF encodings/encryption found in the
wild (scanned PDFs are explicitly out of scope — this is text extraction,
not OCR).
"""

import io

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


def _get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _extract_txt(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Fall back gracefully for files saved with a different encoding
        # rather than failing the whole upload.
        return raw_bytes.decode("latin-1", errors="replace")


def _extract_pdf(raw_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except PdfReadError as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read PDF file. It may be corrupted, encrypted, or scanned (image-only).",
        ) from exc

    if reader.is_encrypted:
        raise HTTPException(
            status_code=400,
            detail="This PDF is password-protected. Please upload an unprotected file.",
        )

    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n".join(pages_text).strip()

    if not full_text:
        raise HTTPException(
            status_code=400,
            detail="No extractable text found in this PDF. It may be a scanned/image-only document.",
        )

    return full_text


async def extract_text_from_upload(file: UploadFile, max_size_bytes: int) -> str:
    """
    Reads an uploaded TXT or PDF file and returns its plain-text content.
    Raises HTTPException (400) for unsupported types, oversized files,
    or files that yield no usable text.
    """
    extension = _get_extension(file.filename or "")
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Only .txt and .pdf are supported.",
        )

    raw_bytes = await file.read()

    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(raw_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {max_mb:.0f}MB size limit.",
        )

    if extension == ".txt":
        return _extract_txt(raw_bytes)

    return _extract_pdf(raw_bytes)
