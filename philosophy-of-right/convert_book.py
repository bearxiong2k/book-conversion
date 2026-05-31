from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, "../.codex_deps")
sys.path.insert(0, "..")

import fitz  # type: ignore

from book_conversion_toolkit import (
    Heading,
    STANDARD_BOOK_CSS,
    clean_spaces,
    render_linked_contents,
    render_standard_nav,
    slugify,
    wrap_html_document,
)


PDF_PATH = Path("Philosophy of Right.pdf")
OUTPUT_PATH = Path("philosophy-of-right.html")

TITLE = "Outlines of the Philosophy of Right"
AUTHOR = "G. W. F. Hegel"
EDITOR = "Translated by T. M. Knox; revised, edited, and introduced by Stephen Houlgate"


@dataclass(frozen=True)
class OutlineEntry:
    pdf_page: int
    level: int
    title: str


# PDF pages are 1-based. These starts are taken from the printed contents.
OUTLINE = [
    OutlineEntry(8, 2, "Introduction"),
    OutlineEntry(16, 3, "Hegel's Philosophical System"),
    OutlineEntry(21, 3, "Freedom"),
    OutlineEntry(40, 2, "Select Bibliography"),
    OutlineEntry(44, 2, "A Chronology of G. W. F. Hegel"),
    OutlineEntry(50, 2, "Preface"),
    OutlineEntry(64, 2, "Introduction to the Philosophy of Right"),
    OutlineEntry(100, 2, "First Part: Abstract Right"),
    OutlineEntry(104, 3, "(1) Property"),
    OutlineEntry(114, 4, "(A) Taking Possession"),
    OutlineEntry(118, 4, "(B) Use of the Thing"),
    OutlineEntry(124, 4, "(C) Alienation of Property"),
    OutlineEntry(131, 3, "(2) Contract"),
    OutlineEntry(140, 3, "(3) Wrong"),
    OutlineEntry(141, 4, "(A) Non-malicious Wrong"),
    OutlineEntry(143, 4, "(B) Fraud"),
    OutlineEntry(143, 4, "(C) Coercion and Crime"),
    OutlineEntry(156, 2, "Second Part: Morality"),
    OutlineEntry(162, 3, "(1) Purpose and Responsibility"),
    OutlineEntry(165, 3, "(2) Intention and Welfare"),
    OutlineEntry(173, 3, "(3) Good and Conscience"),
    OutlineEntry(201, 2, "Third Part: Ethical Life"),
    OutlineEntry(209, 3, "(1) The Family"),
    OutlineEntry(210, 4, "(A) Marriage"),
    OutlineEntry(218, 4, "(B) The Family's Resources"),
    OutlineEntry(219, 4, "(C) The Education of Children and the Dissolution of the Family"),
    OutlineEntry(227, 3, "(2) Civil Society"),
    OutlineEntry(233, 4, "(A) The System of Needs"),
    OutlineEntry(234, 4, "(a) The Nature of Need and its Satisfaction"),
    OutlineEntry(237, 4, "(b) The Nature of Work"),
    OutlineEntry(238, 4, "(c) Resources"),
    OutlineEntry(244, 4, "(B) The Administration of Justice"),
    OutlineEntry(245, 4, "(a) Right as Law"),
    OutlineEntry(250, 4, "(b) The Existence [Dasein] of the Law"),
    OutlineEntry(255, 4, "(c) The Court of Law"),
    OutlineEntry(262, 4, "(C) The Police and the Corporation"),
    OutlineEntry(262, 4, "(a) Police [or the public authority]"),
    OutlineEntry(271, 4, "(b) The Corporation"),
    OutlineEntry(275, 3, "(3) The State"),
    OutlineEntry(282, 4, "(A) Right within the State"),
    OutlineEntry(303, 4, "1. The Internal Constitution for itself"),
    OutlineEntry(310, 4, "(a) The Crown"),
    OutlineEntry(324, 4, "(b) The Executive Power"),
    OutlineEntry(331, 4, "(c) The Legislative Power"),
    OutlineEntry(351, 4, "2. External Sovereignty"),
    OutlineEntry(358, 4, "(B) Right between States"),
    OutlineEntry(362, 4, "(C) World History"),
    OutlineEntry(371, 2, "Explanatory Notes"),
    OutlineEntry(411, 2, "Index"),
]

OMIT_PAGES = {1, 2, 3, 4, 5, 6, 7, 47, 48, 49}
READING_START = 8

GLYPH_REPLACEMENTS = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "oﬀ": "off",
    "diﬃ": "diffi",
}


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    for source, target in GLYPH_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" ,", ",").replace(" .", ".").replace(" ;", ";").replace(" :", ":")
    return text


def line_rows(page: fitz.Page) -> list[dict]:
    rows: list[dict] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = clean_text("".join(span["text"] for span in spans))
            if not text:
                continue
            rows.append(
                {
                    "text": text,
                    "x": line["bbox"][0],
                    "y": line["bbox"][1],
                    "size": max(span["size"] for span in spans),
                    "font": spans[0]["font"] if spans else "",
                }
            )
    return sorted(rows, key=lambda row: (row["y"], row["x"]))


def is_running_header(row: dict, pdf_page: int) -> bool:
    text = row["text"]
    if row["y"] < 48:
        return True
    if text == "This page intentionally left blank":
        return True
    if re.fullmatch(r"[ivxlcdm]+|\d+", text, flags=re.IGNORECASE) and (row["y"] < 80 or row["y"] > 455):
        return True
    return False


def normalize_heading_text(text: str) -> str:
    text = clean_text(text)
    text = text.replace("’", "'")
    return text.upper()


def heading_forms(entry: OutlineEntry) -> set[str]:
    title = normalize_heading_text(entry.title)
    forms = {title}
    if ":" in title:
        forms.update(part.strip() for part in title.split(":") if part.strip())

    match = re.match(r"^\(([A-Z0-9]+)\)\s+(.+)$", title)
    if match:
        marker, rest = match.groups()
        forms.add(rest)
        forms.add(f"{marker}. {rest}")
        forms.add(f"({marker}) {rest}")
        if marker.isdigit():
            forms.add(f"SUB-SECTION {marker}")
            forms.add(f"SECTION {marker}")

    return forms


def heading_matches_row(row: dict, entry: OutlineEntry) -> bool:
    key = normalize_heading_text(row["text"])
    forms = heading_forms(entry)
    if key in forms:
        return True
    if row["size"] >= 10.0:
        return any(len(key) >= 14 and form.startswith(key) for form in forms)
    return False


def is_source_heading(text: str, page_entries: list[OutlineEntry]) -> bool:
    key = normalize_heading_text(text)
    for entry in page_entries:
        forms = heading_forms(entry)
        if key in forms:
            return True
        if any(len(key) >= 14 and form.startswith(key) for form in forms):
            return True
    return key in {
        "INTRODUCTION",
        "PREFACE",
        "SELECT BIBLIOGRAPHY",
        "A CHRONOLOGY OF G. W. F. HEGEL",
        "EXPLANATORY NOTES",
        "INDEX",
        "FIRST PART",
        "SECOND PART",
        "THIRD PART",
        "ABSTRACT RIGHT",
        "MORALITY",
        "ETHICAL LIFE",
}


def append_line(paragraph: str, line: str) -> str:
    if not paragraph:
        return line
    if paragraph.endswith("-") and line and line[0].islower():
        return paragraph[:-1] + line
    return paragraph + " " + line


def flush_paragraph(paragraphs: list[tuple[str, str]], text: str, css: str = "") -> str:
    text = clean_text(text)
    if text:
        paragraphs.append((css, text))
    return ""


def paragraph_rows(rows: list[dict], pdf_page: int, page_entries: list[OutlineEntry]) -> list[tuple[str, str]]:
    paragraphs: list[tuple[str, str]] = []
    current = ""
    current_css = ""
    last_y = 0.0
    last_x = 0.0

    for row in rows:
        text = row["text"]
        if is_running_header(row, pdf_page) or is_source_heading(text, page_entries):
            continue
        if pdf_page >= 411:
            continue
        css = ""
        if row["size"] <= 9.6 or row["x"] > 50:
            css = "noteish" if pdf_page >= 371 else "addition"
        starts_new = False
        if not current:
            starts_new = False
        elif row["y"] - last_y > 15:
            starts_new = True
        elif row["x"] - last_x > 7:
            starts_new = True
        elif re.match(r"^(\d{1,3}\.|Addition:|Remark:|[A-Z][A-Za-z’' -]+:)", text):
            starts_new = True
        if starts_new:
            current = flush_paragraph(paragraphs, current, current_css)
            current_css = css
        if not current:
            current_css = css
        current = append_line(current, text)
        last_y = row["y"]
        last_x = row["x"]
    flush_paragraph(paragraphs, current, current_css)
    return paragraphs


def render_paragraph(css: str, text: str) -> str:
    class_attr = f' class="{css}"' if css else ""
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"^(§?\d{1,3}\.?)\s+", r'<span class="section-number">\1</span> ', escaped)
    escaped = re.sub(r"^(Addition:|Remark:)\s+", r'<span class="label">\1</span> ', escaped)
    return f"<p{class_attr}>{escaped}</p>"


def render_heading(heading: Heading) -> str:
    return f'<h{heading.level} id="{heading.ident}">{html.escape(heading.text, quote=False)}</h{heading.level}>'


def emit_paragraph(
    fragments: list[str],
    paragraph: str,
    css: str,
) -> str:
    paragraph = clean_text(paragraph)
    if paragraph:
        fragments.append(render_paragraph(css, paragraph))
    return ""


def insert_unplaced_headings(fragments: list[str], headings: list[Heading]) -> list[str]:
    if not headings:
        return fragments

    rendered = [render_heading(heading) for heading in headings]
    if fragments and paragraph_inner(fragments[0]) and plain_start(fragments[0]).islower():
        return fragments[:1] + rendered + fragments[1:]
    return rendered + fragments


def page_content_fragments(
    rows: list[dict],
    pdf_page: int,
    page_entries: list[OutlineEntry],
    page_headings: list[Heading],
) -> list[str]:
    fragments: list[str] = []
    current = ""
    current_css = ""
    last_y = 0.0
    last_x = 0.0
    pending = list(zip(page_entries, page_headings))

    for row in rows:
        text = row["text"]
        if is_running_header(row, pdf_page):
            continue

        matched_heading_index = next(
            (index for index, (entry, _heading) in enumerate(pending) if heading_matches_row(row, entry)),
            None,
        )
        if matched_heading_index is not None:
            current = emit_paragraph(fragments, current, current_css)
            _entry, heading = pending.pop(matched_heading_index)
            fragments.append(render_heading(heading))
            current_css = ""
            last_y = 0.0
            last_x = 0.0
            continue

        if is_source_heading(text, page_entries):
            continue

        css = ""
        if row["size"] <= 9.6 or row["x"] > 50:
            css = "noteish" if pdf_page >= 371 else "addition"
        starts_new = False
        if not current:
            starts_new = False
        elif row["y"] - last_y > 15:
            starts_new = True
        elif row["x"] - last_x > 7:
            starts_new = True
        elif re.match(r"^(\d{1,3}\.|Addition:|Remark:|[A-Z][A-Za-z’' -]+:)", text):
            starts_new = True
        if starts_new:
            current = emit_paragraph(fragments, current, current_css)
            current_css = css
        if not current:
            current_css = css
        current = append_line(current, text)
        last_y = row["y"]
        last_x = row["x"]

    emit_paragraph(fragments, current, current_css)
    return insert_unplaced_headings(fragments, [heading for _entry, heading in pending])


def render_index_page(rows: list[dict]) -> str:
    columns = [[], []]
    for row in rows:
        if is_running_header(row, 411) or row["text"] == "INDEX":
            continue
        col = 0 if row["x"] < 165 else 1
        columns[col].append(row)
    parts = []
    for column in columns:
        lines = [html.escape(row["text"], quote=False) for row in sorted(column, key=lambda row: (row["y"], row["x"]))]
        parts.append("<pre>" + "\n".join(lines) + "</pre>")
    return '<div class="index-columns">' + "\n".join(parts) + "</div>"


def paragraph_inner(markup: str) -> tuple[str, str] | None:
    match = re.fullmatch(r'<p(?P<attrs>[^>]*)>(?P<inner>.*)</p>', markup, flags=re.DOTALL)
    if not match:
        return None
    return match.group("attrs"), match.group("inner")


def plain_start(markup: str) -> str:
    text = re.sub(r"<[^>]+>", "", markup)
    text = html.unescape(text).strip()
    return text[:1]


def paragraph_can_continue(inner: str) -> bool:
    text = html.unescape(re.sub(r"<[^>]+>", "", inner)).rstrip()
    return bool(text) and (text.endswith("-") or not re.search(r"[.!?]['\")\]]*$", text))


def merge_body_fragments(items: list[str]) -> list[str]:
    merged: list[str] = []
    for item in items:
        current = paragraph_inner(item)
        previous = paragraph_inner(merged[-1]) if merged else None
        if current and previous:
            prev_attrs, prev_inner = previous
            current_attrs, current_inner = current
            starts_lower = plain_start(current_inner).islower()
            if prev_attrs == current_attrs and (starts_lower or prev_inner.rstrip().endswith("-")):
                if prev_inner.rstrip().endswith("-"):
                    joined = prev_inner.rstrip()[:-1] + current_inner.lstrip()
                else:
                    joined = prev_inner.rstrip() + " " + current_inner.lstrip()
                merged[-1] = f"<p{prev_attrs}>{joined}</p>"
                continue
            if current_attrs == "" and starts_lower:
                merged_into_prior = False
                for index in range(len(merged) - 1, -1, -1):
                    candidate = paragraph_inner(merged[index])
                    if not candidate:
                        break
                    candidate_attrs, candidate_inner = candidate
                    if candidate_attrs == "":
                        break
                    if 'class="addition"' in candidate_attrs and paragraph_can_continue(candidate_inner):
                        joined = candidate_inner.rstrip() + " " + current_inner.lstrip()
                        merged[index] = f"<p{candidate_attrs}>{joined}</p>"
                        merged_into_prior = True
                        break
                    if 'class="addition"' not in candidate_attrs and 'class="noteish"' not in candidate_attrs:
                        break
                if merged_into_prior:
                    continue
                for index in range(len(merged) - 1, -1, -1):
                    candidate = paragraph_inner(merged[index])
                    if not candidate:
                        break
                    candidate_attrs, candidate_inner = candidate
                    if candidate_attrs == "" and paragraph_can_continue(candidate_inner):
                        joined = candidate_inner.rstrip() + " " + current_inner.lstrip()
                        merged[index] = f"<p>{joined}</p>"
                        break
                    if candidate_attrs == "":
                        break
                    if 'class="addition"' not in candidate_attrs and 'class="noteish"' not in candidate_attrs:
                        break
                else:
                    merged.append(item)
                    continue
                continue
        merged.append(item)
    return merged


def render_title_page() -> str:
    return (
        '<section id="title" class="title-page" aria-labelledby="title-heading">\n'
        '<p class="series">Oxford World\'s Classics</p>\n'
        f'<h1 id="title-heading">{html.escape(TITLE)}</h1>\n'
        f'<p class="author">{html.escape(AUTHOR)}</p>\n'
        f'<p class="subtitle">{html.escape(EDITOR)}</p>\n'
        "</section>"
    )


def build_html() -> str:
    doc = fitz.open(PDF_PATH)
    used_ids = {"title", "title-heading", "contents"}
    headings = [Heading(2, "Title", "title"), Heading(2, "Contents", "contents")]
    heading_by_page: dict[int, list[Heading]] = {}
    entries_by_page: dict[int, list[OutlineEntry]] = {}
    for entry in OUTLINE:
        ident = slugify(entry.title, used_ids)
        heading = Heading(entry.level, entry.title, ident)
        headings.append(heading)
        heading_by_page.setdefault(entry.pdf_page, []).append(heading)
        entries_by_page.setdefault(entry.pdf_page, []).append(entry)

    body = [render_title_page(), render_linked_contents(headings, max_level=4)]
    for pdf_page in range(READING_START, doc.page_count + 1):
        if pdf_page in OMIT_PAGES:
            continue
        rows = line_rows(doc[pdf_page - 1])
        page_entries = entries_by_page.get(pdf_page, [])
        if pdf_page >= 411:
            for heading in heading_by_page.get(pdf_page, []):
                body.append(render_heading(heading))
            if pdf_page == 411:
                body.append(render_index_page(rows))
            else:
                body.append(render_index_page(rows))
            continue
        body.extend(page_content_fragments(rows, pdf_page, page_entries, heading_by_page.get(pdf_page, [])))

    body = merge_body_fragments(body)
    css = (
        STANDARD_BOOK_CSS
        + "\n.title-page{min-height:72vh;display:flex;flex-direction:column;justify-content:center;text-align:center}"
        + "\n.title-page .series{font-variant:small-caps;letter-spacing:.12em;color:#5c5449}"
        + "\n.addition{margin-left:1.25rem;font-size:.96rem;color:#39342f}"
        + "\n.noteish{margin-left:1.25rem;font-size:.92rem;color:#39342f}"
        + "\n.section-number,.label{font-weight:700;color:#2f2a24}"
        + "\n.index-columns{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:18px}"
        + "\n.index-columns pre{white-space:pre-wrap;margin:0;font:.84rem/1.32 Georgia,'Times New Roman',serif}"
        + "\n@media (max-width:680px){.index-columns{grid-template-columns:1fr}}"
    )
    return wrap_html_document(TITLE, "\n".join(body), render_standard_nav(headings), css=css)


def main() -> None:
    OUTPUT_PATH.write_text(build_html(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
