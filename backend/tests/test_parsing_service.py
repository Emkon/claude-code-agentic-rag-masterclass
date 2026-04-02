import os
import pytest
from unittest.mock import MagicMock, patch, call

import app.services.parsing_service as parsing_module
from app.services.parsing_service import parse_document

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level _converter singleton before and after each test."""
    parsing_module._converter = None
    yield
    parsing_module._converter = None


def _mock_converter(markdown_output: str) -> MagicMock:
    """Build a fake DocumentConverter whose convert() returns markdown_output."""
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = markdown_output
    mock_conv = MagicMock()
    mock_conv.convert.return_value = mock_result
    return mock_conv


# ---------------------------------------------------------------------------
# Format routing — correct suffix is passed to convert()
# ---------------------------------------------------------------------------

async def test_parse_pdf_returns_text():
    mock_conv = _mock_converter("# Report\n\nThis is the content.")
    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        result = await parse_document(b"fake pdf bytes", "report.pdf")
    assert result == "# Report\n\nThis is the content."
    mock_conv.convert.assert_called_once()
    path_used = mock_conv.convert.call_args[0][0]
    assert path_used.endswith(".pdf")


async def test_parse_docx_returns_text():
    mock_conv = _mock_converter("# Memo\n\nContent from docx.")
    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        result = await parse_document(b"fake docx bytes", "memo.docx")
    assert result == "# Memo\n\nContent from docx."
    path_used = mock_conv.convert.call_args[0][0]
    assert path_used.endswith(".docx")


async def test_parse_html_returns_text():
    mock_conv = _mock_converter("# Page Title\n\nBody text here.")
    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        result = await parse_document(b"<html><body>...</body></html>", "page.html")
    assert result == "# Page Title\n\nBody text here."
    path_used = mock_conv.convert.call_args[0][0]
    assert path_used.endswith(".html")


async def test_parse_markdown_returns_text():
    mock_conv = _mock_converter("# Notes\n\n- item one\n- item two")
    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        result = await parse_document(b"# Notes\n\n- item one", "notes.md")
    assert result == "# Notes\n\n- item one\n- item two"
    path_used = mock_conv.convert.call_args[0][0]
    assert path_used.endswith(".md")


async def test_parse_markdown_alt_extension():
    mock_conv = _mock_converter("Some markdown content.")
    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        result = await parse_document(b"Some markdown content.", "readme.markdown")
    assert result == "Some markdown content."
    path_used = mock_conv.convert.call_args[0][0]
    assert path_used.endswith(".markdown")


# ---------------------------------------------------------------------------
# Temp file lifecycle — always cleaned up
# ---------------------------------------------------------------------------

async def test_tempfile_deleted_after_success():
    captured_paths: list[str] = []

    mock_conv = _mock_converter("Some text.")

    original_convert = mock_conv.convert.side_effect

    def capturing_convert(path):
        captured_paths.append(path)
        return mock_conv.convert.return_value

    mock_conv.convert.side_effect = capturing_convert

    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        await parse_document(b"bytes", "doc.pdf")

    assert len(captured_paths) == 1
    assert not os.path.exists(captured_paths[0]), "Temp file was not deleted after success"


async def test_tempfile_deleted_after_failure():
    captured_paths: list[str] = []

    mock_conv = MagicMock()

    def capturing_convert(path):
        captured_paths.append(path)
        raise RuntimeError("corrupt file")

    mock_conv.convert.side_effect = capturing_convert

    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        with pytest.raises(ValueError):
            await parse_document(b"bad bytes", "bad.docx")

    assert len(captured_paths) == 1
    assert not os.path.exists(captured_paths[0]), "Temp file was not deleted after failure"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

async def test_docling_exception_raises_value_error():
    mock_conv = MagicMock()
    mock_conv.convert.side_effect = Exception("parse error")

    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        with pytest.raises(ValueError) as exc_info:
            await parse_document(b"bytes", "report.pdf")

    assert "report.pdf" in str(exc_info.value)
    assert "parse error" in str(exc_info.value)


async def test_empty_output_returns_empty_string():
    """Whitespace-only output is stripped to empty string.
    ingestion_service checks `if not full_text` to catch this case."""
    mock_conv = _mock_converter("   \n\t  ")
    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        result = await parse_document(b"bytes", "empty.pdf")
    assert result == ""


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------

async def test_singleton_reused_across_calls():
    """DocumentConverter() constructor must be called exactly once across multiple parse calls."""
    mock_conv = _mock_converter("text")

    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv) as mock_cls:
        await parse_document(b"bytes1", "a.pdf")
        await parse_document(b"bytes2", "b.pdf")

    mock_cls.assert_called_once()


# ---------------------------------------------------------------------------
# Bytes integrity — exactly the provided bytes reach the temp file
# ---------------------------------------------------------------------------

async def test_bytes_written_to_tempfile():
    """The exact file_bytes passed in must be written to the temp file."""
    file_bytes = b"exact content 12345"
    written_data: list[bytes] = []

    mock_conv = _mock_converter("text")
    # Capture the pre-built return value before setting side_effect — calling
    # the mock inside its own side_effect would cause infinite recursion.
    mock_result = mock_conv.convert.return_value

    def capturing_convert(path):
        with open(path, "rb") as f:
            written_data.append(f.read())
        return mock_result

    mock_conv.convert.side_effect = capturing_convert

    with patch("app.services.parsing_service.DocumentConverter", return_value=mock_conv):
        await parse_document(file_bytes, "test.pdf")

    assert len(written_data) == 1
    assert written_data[0] == file_bytes, "Bytes written to temp file do not match input"
