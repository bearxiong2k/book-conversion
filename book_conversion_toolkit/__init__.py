"""Shared helpers for script-driven book-to-HTML conversions."""

from .html import (
    DEFAULT_BOOK_CSS,
    DEFAULT_FOOTNOTE_JS,
    SUBLIME_BOOK_CSS,
    Footnote,
    Heading,
    HtmlValidationReport,
    render_footnote_list,
    render_footnote_ref,
    render_nav,
    render_sublime_nav,
    validate_html,
    wrap_html_document,
)
from .sources import PDFLine, EPUBPackage, ensure_ocr_cache, extract_pdf_lines, require_fitz
from .text import (
    apply_replacements,
    clean_spaces,
    join_wrapped_lines,
    looks_sentence_closed,
    slugify,
)

__all__ = [
    "DEFAULT_BOOK_CSS",
    "DEFAULT_FOOTNOTE_JS",
    "EPUBPackage",
    "Footnote",
    "Heading",
    "HtmlValidationReport",
    "PDFLine",
    "SUBLIME_BOOK_CSS",
    "apply_replacements",
    "clean_spaces",
    "ensure_ocr_cache",
    "extract_pdf_lines",
    "join_wrapped_lines",
    "looks_sentence_closed",
    "render_footnote_list",
    "render_footnote_ref",
    "render_nav",
    "render_sublime_nav",
    "require_fitz",
    "slugify",
    "validate_html",
    "wrap_html_document",
]
