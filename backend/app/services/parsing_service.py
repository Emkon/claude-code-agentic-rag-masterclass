import asyncio
import os
import tempfile
from pathlib import Path
from docling.document_converter import DocumentConverter

_converter: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter


async def parse_document(file_bytes: bytes, filename: str) -> str:
    """
    Parse PDF, DOCX, HTML, or Markdown into markdown text using docling.
    Runs synchronous conversion in a thread executor to avoid blocking the event loop.
    Raises ValueError on failure with a descriptive message.
    """
    suffix = Path(filename).suffix.lower() or ".tmp"
    tmp_path = None

    try:
        # delete=False required on Windows — OS holds a file lock while the
        # context manager is open, preventing docling from opening the same path.
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        converter = _get_converter()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: converter.convert(tmp_path)
        )
        return result.document.export_to_markdown().strip()

    except Exception as exc:
        raise ValueError(f"Failed to parse '{filename}': {exc}") from exc

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
