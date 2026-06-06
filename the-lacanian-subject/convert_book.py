from __future__ import annotations

import html
import re
import subprocess
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
    join_wrapped_lines,
    merge_continuation_paragraphs,
    render_linked_contents,
    render_standard_nav,
    slugify,
    wrap_html_document,
)


PDF_PATH = Path("The Lacanian Subject.pdf")
OUTPUT_PATH = Path("the-lacanian-subject.html")
TMP_DIR = Path("tmp")
OCR_DIR = TMP_DIR / "ocr"
IMAGE_DIR = TMP_DIR / "ocr-images"

TITLE = "The Lacanian Subject"
SUBTITLE = "Between Language and Jouissance"
AUTHOR = "Bruce Fink"


@dataclass(frozen=True)
class OutlineEntry:
    pdf_page: int
    level: int
    title: str


OUTLINE = [
    OutlineEntry(12, 2, "Preface"),
    OutlineEntry(20, 2, "Part One: Structure: Alienation and the Other"),
    OutlineEntry(22, 2, "1 Language and Otherness"),
    OutlineEntry(22, 3, "A Slip of the Other's Tongue"),
    OutlineEntry(26, 3, "The Unconscious"),
    OutlineEntry(30, 3, "Foreign Bodies"),
    OutlineEntry(33, 2, "2 The Nature of Unconscious Thought, or How the Other Half Thinks"),
    OutlineEntry(35, 3, "Heads or Tails"),
    OutlineEntry(38, 3, "Randomness and Memory"),
    OutlineEntry(39, 3, "The Unconscious Assembles"),
    OutlineEntry(41, 3, "Knowledge without a Subject"),
    OutlineEntry(43, 2, "3 The Creative Function of the Word: The Symbolic and the Real"),
    OutlineEntry(45, 3, "Trauma"),
    OutlineEntry(47, 3, "Interpretation Hits the Cause"),
    OutlineEntry(48, 3, "Incompleteness of the Symbolic Order: The (W)hole in the Other"),
    OutlineEntry(49, 3, "Kinks in the Symbolic Order"),
    OutlineEntry(50, 3, "Structure versus Cause"),
    OutlineEntry(54, 2, "Part Two: The Lacanian Subject"),
    OutlineEntry(54, 2, "4 The Lacanian Subject"),
    OutlineEntry(55, 3, 'The Lacanian Subject Is Not the "Individual" or Conscious Subject of Anglo-American Philosophy'),
    OutlineEntry(56, 3, "The Lacanian Subject Is Not the Subject of the Statement"),
    OutlineEntry(57, 3, "The Lacanian Subject Appears Nowhere in What Is Said"),
    OutlineEntry(60, 3, "The Fleetingness of the Subject"),
    OutlineEntry(61, 3, "The Freudian Subject"),
    OutlineEntry(62, 3, "The Cartesian Subject and Its Inverse"),
    OutlineEntry(63, 3, "Lacan's Split Subject"),
    OutlineEntry(65, 3, "Beyond the Split Subject"),
    OutlineEntry(68, 2, "5 The Subject and the Other's Desire"),
    OutlineEntry(68, 3, "Alienation and Separation"),
    OutlineEntry(70, 3, "The Vel of Alienation"),
    OutlineEntry(72, 3, "Desire and Lack in Separation"),
    OutlineEntry(74, 3, "The Introduction of a Third Term"),
    OutlineEntry(78, 3, "Object a: The Other's Desire"),
    OutlineEntry(80, 3, "A Further Separation: The Traversing of Fantasy"),
    OutlineEntry(82, 3, "Subjectifying the Cause: A Temporal Conundrum"),
    OutlineEntry(85, 3, "Alienation, Separation, and the Traversing of Fantasy in the Analytic Setting"),
    OutlineEntry(88, 2, "6 Metaphor and the Precipitation of Subjectivity"),
    OutlineEntry(89, 3, "The Signified"),
    OutlineEntry(91, 3, "Two Faces of the Psychoanalytic Subject"),
    OutlineEntry(91, 3, "The Subject as Signified"),
    OutlineEntry(96, 3, "The Subject as Breach"),
    OutlineEntry(102, 2, "Part Three: The Lacanian Object: Love, Desire, Jouissance"),
    OutlineEntry(102, 2, "7 Object (a): Cause of Desire"),
    OutlineEntry(103, 3, "Object Relations"),
    OutlineEntry(103, 3, "Imaginary Objects, Imaginary Relations"),
    OutlineEntry(106, 3, "The Other as Object, Symbolic Relations"),
    OutlineEntry(109, 3, "Real Objects, Encounters with the Real"),
    OutlineEntry(112, 3, "Lost Objects"),
    OutlineEntry(114, 3, "The Freudian Thing"),
    OutlineEntry(115, 3, "Surplus Value, Surplus Jouissance"),
    OutlineEntry(117, 2, "8 There's No Such Thing as a Sexual Relationship"),
    OutlineEntry(118, 3, "Castration"),
    OutlineEntry(120, 3, "The Phallus and the Phallic Function"),
    OutlineEntry(123, 3, "There's No Such Thing as a Sexual Relationship"),
    OutlineEntry(124, 3, "Distinguishing between the Sexes"),
    OutlineEntry(127, 3, "The Formulas of Sexuation"),
    OutlineEntry(132, 3, "A Dissymmetry of Partners"),
    OutlineEntry(134, 3, "Woman Does Not Exist"),
    OutlineEntry(136, 3, "Masculine/Feminine-Signifier/Signifierness"),
    OutlineEntry(138, 3, "Other to Herself, Other Jouissance"),
    OutlineEntry(140, 3, "The Truth of Psychoanalysis"),
    OutlineEntry(141, 3, "Existence and Ex-sistence"),
    OutlineEntry(142, 3, "A New Metaphor for Sexual Difference"),
    OutlineEntry(148, 2, "Part Four: The Status of Psychoanalytic Discourse"),
    OutlineEntry(148, 2, "9 The Four Discourses"),
    OutlineEntry(149, 3, "The Master's Discourse"),
    OutlineEntry(151, 3, "The University Discourse"),
    OutlineEntry(152, 3, "The Hysteric's Discourse"),
    OutlineEntry(154, 3, "The Analyst's Discourse"),
    OutlineEntry(155, 3, "The Social Situation of Psychoanalysis"),
    OutlineEntry(156, 3, "There's No Such Thing as a Metalanguage"),
    OutlineEntry(157, 2, "10 Psychoanalysis and Science"),
    OutlineEntry(157, 3, "Science as Discourse"),
    OutlineEntry(158, 3, "Suturing the Subject"),
    OutlineEntry(160, 3, "Science, the Hysteric's Discourse, and Psychoanalytic Theory"),
    OutlineEntry(161, 3, 'The Three Registers and Differently "Polarized" Discourses'),
    OutlineEntry(163, 3, "Formalization and the Transmissibility of Psychoanalysis"),
    OutlineEntry(164, 3, "The Status of Psychoanalysis"),
    OutlineEntry(165, 3, "The Ethics of Lacanian Psychoanalysis"),
    OutlineEntry(166, 2, "Afterword"),
    OutlineEntry(172, 2, "Appendix 1: The Language of the Unconscious"),
    OutlineEntry(184, 2, "Appendix 2: Stalking the Cause"),
    OutlineEntry(192, 2, "Glossary of Lacanian Symbols"),
    OutlineEntry(194, 2, "Acknowledgments"),
    OutlineEntry(196, 2, "Notes"),
    OutlineEntry(226, 2, "Bibliography"),
    OutlineEntry(232, 2, "Index"),
]

OMIT_PAGES = set(range(1, 12)) | {19, 225, 231}
READING_START = 12

TEXT_REPLACEMENTS = {
    "LacaN": "Lacan",
    "Alll Rights Reserved": "All Rights Reserved",
    "Gédelian": "Gödelian",
    "Wenran Does Not Exist": "Woman Does Not Exist",
    "Wenran": "Woman",
    "mOther": "mOther",
    "lacan": "Lacan",
    "Ecrits": "Écrits",
    "Ecole de la Cause freudienne": "École de la Cause freudienne",
    "jouissance:.a": "jouissance: a",
    "““Gödelian": "“Gödelian",
    "part |": "part 1",
    "struc- ture": "structure",
    "dis- course": "discourse",
    "psychoanaly- sis": "psychoanalysis",
}


def render_title_page() -> str:
    return (
        '<section id="title" class="title-page" aria-labelledby="title-heading">\n'
        f'<h1 id="title-heading">{html.escape(TITLE, quote=False)}</h1>\n'
        f'<p class="subtitle">{html.escape(SUBTITLE, quote=False)}</p>\n'
        f'<p class="author">{html.escape(AUTHOR, quote=False)}</p>\n'
        '<p class="dedication">Pour Héloise</p>\n'
        "</section>"
    )


def ocr_page(pdf: fitz.Document, pdf_page: int) -> str:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    text_path = OCR_DIR / f"page-{pdf_page:03d}.txt"
    if text_path.exists():
        return text_path.read_text(encoding="utf-8")

    image_path = IMAGE_DIR / f"page-{pdf_page:03d}.png"
    page = pdf[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.6, 2.6), alpha=False)
    pix.save(image_path)
    result = subprocess.run(
        ["tesseract", str(image_path), "stdout"],
        check=True,
        text=True,
        capture_output=True,
    )
    text_path.write_text(result.stdout, encoding="utf-8")
    return result.stdout


def normalize_key(text: str) -> str:
    value = html.unescape(text).lower().replace("’", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def cleanup_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\x0c", "")
    text = re.sub(r"^\d{1,3}\s+(?:NOTES TO|BIBLIOGRAPHY|INDEX)\b[A-Z0-9 ]*(?=\s+[a-z])", "", text)
    text = re.sub(r"([a-z])- ([a-z])", r"\1\2", text)
    text = clean_spaces(text, TEXT_REPLACEMENTS)
    text = re.sub(r"^(\d{1,3}),\s+", r"\1. ", text)
    text = re.sub(r"\b([A-Z]) ([A-Z])\b", r"\1\2", text)
    return text


def is_running_header(line: str, nonblank_index: int) -> bool:
    text = cleanup_text(line)
    if not text:
        return True
    if nonblank_index > 1:
        return False
    if re.fullmatch(r"[ivxlcdm]+", text, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"\d{1,3}", text):
        return True
    if re.fullmatch(r"[ivxlcdm]+\s+[A-Z][A-Z ':-]+", text, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"[A-Z][A-Z ':-]+\s+[ivxlcdm]+", text, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"\d{1,3}\s+CHAPTER\s+\d+", text, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"\d{1,3}\s+NOTES TO .+", text):
        return True
    if re.fullmatch(r"\d{1,3}\s+(?:BIBLIOGRAPHY|INDEX)", text):
        return True
    if re.fullmatch(r"[A-Z][A-Z ':-]+\s+\d{1,3}", text) and len(text) < 64:
        return True
    if re.fullmatch(r"NOTES TO .+\s+\d{1,3}", text):
        return True
    return False


def page_blocks(raw_text: str) -> list[str]:
    lines = raw_text.splitlines()
    filtered: list[str] = []
    nonblank_index = 0
    for line in lines:
        if cleanup_text(line):
            nonblank_index += 1
        if is_running_header(line, nonblank_index):
            filtered.append("")
        else:
            filtered.append(line.rstrip())

    blocks: list[str] = []
    current: list[str] = []
    for line in filtered:
        if not cleanup_text(line):
            if current:
                blocks.append(join_wrapped_lines(current, TEXT_REPLACEMENTS))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(join_wrapped_lines(current, TEXT_REPLACEMENTS))
    return [cleanup_text(block) for block in blocks if cleanup_text(block)]


def heading_candidates(entry: OutlineEntry) -> set[str]:
    candidates = {entry.title}
    title = re.sub(r"^\d+\s+", "", entry.title)
    if title != entry.title:
        candidates.add(title)
    if ": " in entry.title:
        candidates.update(part.strip() for part in entry.title.split(":") if part.strip())
    candidates.add(entry.title.replace("'", "’"))
    candidates.add(entry.title.replace('"', ""))
    return {normalize_key(candidate) for candidate in candidates if candidate}


def render_heading(heading: Heading) -> str:
    return f'<h{heading.level} id="{heading.ident}">{html.escape(heading.text, quote=False)}</h{heading.level}>'


def render_paragraph(block: str, pdf_page: int) -> str:
    escaped = html.escape(block, quote=False)
    escaped = re.sub(r"\bS\((?:A|4)\)", 'S(<span class="math-symbol">Ⱥ</span>)', escaped)
    klass = ""
    if pdf_page >= 196 and pdf_page < 226:
        klass = ' class="noteish"'
    elif pdf_page >= 226 and pdf_page < 232:
        klass = ' class="bibliography-entry"'
    elif pdf_page >= 232:
        klass = ' class="index-entry"'
    return f"<p{klass}>{escaped}</p>"


def build_html() -> str:
    pdf = fitz.open(PDF_PATH)
    used_ids = {"title", "title-heading", "contents"}
    headings = [Heading(2, "Title", "title"), Heading(2, "Contents", "contents")]
    entries_by_page: dict[int, list[OutlineEntry]] = {}
    heading_by_entry: dict[OutlineEntry, Heading] = {}
    heading_keys: dict[str, OutlineEntry] = {}

    for entry in OUTLINE:
        ident = slugify(entry.title, used_ids)
        heading = Heading(entry.level, entry.title, ident)
        headings.append(heading)
        entries_by_page.setdefault(entry.pdf_page, []).append(entry)
        heading_by_entry[entry] = heading
        for key in heading_candidates(entry):
            heading_keys.setdefault(key, entry)

    emitted_headings: set[OutlineEntry] = set()
    fragments: list[str] = [render_title_page(), render_linked_contents(headings, max_level=3)]

    for pdf_page in range(READING_START, pdf.page_count + 1):
        if pdf_page in OMIT_PAGES:
            continue
        for entry in entries_by_page.get(pdf_page, []):
            if entry not in emitted_headings:
                fragments.append(render_heading(heading_by_entry[entry]))
                emitted_headings.add(entry)

        for block in page_blocks(ocr_page(pdf, pdf_page)):
            key = normalize_key(block)
            entry = heading_keys.get(key)
            if entry is not None:
                if entry not in emitted_headings:
                    fragments.append(render_heading(heading_by_entry[entry]))
                    emitted_headings.add(entry)
                continue
            if key in {"part one", "part two", "part three", "part four"}:
                continue
            fragments.append(render_paragraph(block, pdf_page))

    fragments = merge_continuation_paragraphs(fragments)
    css = (
        STANDARD_BOOK_CSS
        + "\n.title-page{min-height:72vh;display:flex;flex-direction:column;justify-content:center;text-align:center}"
        + "\n.title-page .subtitle{font-size:1.15rem;color:#5c5449}"
        + "\n.noteish,.bibliography-entry{font-size:.92rem;color:#39342f}"
        + "\n.index-entry{font-size:.9rem;line-height:1.35}"
        + "\n.math-symbol{font-family:Georgia,'Times New Roman',serif;font-style:italic}"
    )
    return wrap_html_document(TITLE, "\n".join(fragments), render_standard_nav(headings), css=css)


def main() -> None:
    markup = build_html()
    OUTPUT_PATH.write_text(markup, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Annotation blocks pending toolkit wrapper: {markup.count('<p')}")


if __name__ == "__main__":
    main()
