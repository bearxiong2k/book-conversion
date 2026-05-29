from __future__ import annotations

import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from .text import clean_spaces


@dataclass(frozen=True)
class PDFLine:
    page: int
    y: float
    x0: float
    x1: float
    text: str


def require_fitz() -> Any:
    repo_root = Path(__file__).resolve().parents[1]
    for dep_dir in (Path.cwd() / ".codex_deps", repo_root / ".codex_deps"):
        if dep_dir.exists():
            sys.path.insert(0, str(dep_dir))
    try:
        import fitz  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PyMuPDF is required. Run `python3 -m pip install --target .codex_deps pymupdf` "
            "or install the root requirements."
        ) from exc
    return fitz


def extract_pdf_lines(
    page: Any,
    page_number: int,
    top: float = 0,
    bottom: float | None = None,
    min_text: bool = True,
) -> list[PDFLine]:
    """Extract text lines from a PyMuPDF page, sorted by visual position."""

    pieces: list[tuple[float, float, float, str]] = []
    bottom = bottom if bottom is not None else page.rect.y1
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            text = clean_spaces(text)
            if min_text and not text:
                continue
            x0, y0, x1, _ = line["bbox"]
            if y0 < top or y0 > bottom:
                continue
            pieces.append((y0, x0, x1, text))

    rows: list[list[tuple[float, float, float, str]]] = []
    for piece in sorted(pieces, key=lambda item: (item[0], item[1])):
        if rows and abs(rows[-1][0][0] - piece[0]) < 2.2:
            rows[-1].append(piece)
        else:
            rows.append([piece])

    lines: list[PDFLine] = []
    for row in rows:
        row = sorted(row, key=lambda item: item[1])
        text = clean_spaces(" ".join(item[3] for item in row))
        if text or not min_text:
            lines.append(PDFLine(page_number, min(item[0] for item in row), min(item[1] for item in row), max(item[2] for item in row), text))
    return lines


def ensure_ocr_cache(
    doc: Any,
    ocr_dir: Path,
    image_dir: Path,
    pages: Iterable[int] | None = None,
    scale: float = 3.0,
    psm: int = 6,
) -> None:
    """Render selected one-based PDF pages and cache Tesseract OCR text."""

    fitz = require_fitz()
    ocr_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    page_numbers = list(pages) if pages is not None else list(range(1, doc.page_count + 1))
    for page_number in page_numbers:
        output = ocr_dir / f"page-{page_number:03d}.txt"
        if output.exists() and output.stat().st_size:
            continue
        image = image_dir / f"page-{page_number:03d}.png"
        if not image.exists():
            pix = doc[page_number - 1].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            pix.save(image)
        result = subprocess.run(
            ["tesseract", str(image), "stdout", "--psm", str(psm)],
            check=True,
            capture_output=True,
            text=True,
        )
        output.write_text(result.stdout, encoding="utf-8")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class EPUBPackage:
    """Small helper for reading EPUB spine order and extracting members."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _container_opf_path(self, archive: zipfile.ZipFile) -> str:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(node for node in container.iter() if _local_name(node.tag) == "rootfile")
        return rootfile.attrib["full-path"]

    def spine(self) -> list[str]:
        with zipfile.ZipFile(self.path) as archive:
            opf_path = self._container_opf_path(archive)
            opf_dir = str(Path(opf_path).parent).replace(".", "")
            root = ET.fromstring(archive.read(opf_path))
            manifest = {
                node.attrib["id"]: node.attrib["href"]
                for node in root.iter()
                if _local_name(node.tag) == "item" and "id" in node.attrib and "href" in node.attrib
            }
            spine_ids = [
                node.attrib["idref"]
                for node in root.iter()
                if _local_name(node.tag) == "itemref" and "idref" in node.attrib
            ]
            return [
                str(Path(opf_dir, manifest[item_id])).replace("\\", "/")
                for item_id in spine_ids
                if item_id in manifest
            ]

    def read_text(self, member: str) -> str:
        with zipfile.ZipFile(self.path) as archive:
            return archive.read(member).decode("utf-8")

    def extract_member(self, member: str, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.path) as archive:
            data = archive.read(member)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
        return target
