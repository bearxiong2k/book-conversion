from __future__ import annotations

import csv
import html
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, "../sublime-object-of-ideaology/.codex_deps")
sys.path.insert(0, "..")

import fitz  # type: ignore

from book_conversion_toolkit import Heading, SUBLIME_BOOK_CSS, render_linked_contents, render_sublime_nav, wrap_html_document


PDF_PATH = next(Path(".").glob("*.pdf"))
OUTPUT_PATH = Path("the-idea-of-phenomenology.html")
TMP_DIR = Path("tmp")
OCR_DIR = TMP_DIR / "ocr"
PNG_DIR = TMP_DIR / "pdfs"
INDEX_TSV_DIR = TMP_DIR / "index_tsv"


OMIT_PAGES = {0, 1, 3}
INDEX_PAGES = {70, 71}

SECTION_IDS = {
    "TRANSLATOR'S INTRODUCTION": "translators-introduction",
    "TRANSLATOR’S INTRODUCTION": "translators-introduction",
    "LECTURE I": "lecture-i",
    "LECTURE II": "lecture-ii",
    "LECTURE III": "lecture-iii",
    "LECTURE IV": "lecture-iv",
    "LECTURE V": "lecture-v",
    "ADDENDA": "addenda",
    "ADDENDUM I": "addendum-i",
    "ADDENDUM II": "addendum-ii",
    "ADDENDUM III": "addendum-iii",
    "THE TRAIN OF THOUGHT IN THE LECTURES": "train-of-thought",
    "A. THE FIRST STEP IN THE PHENOMENOLOGICAL CONSIDERATION": "train-first-step",
    "B. THE SECOND STEP IN THE PHENOMENOLOGICAL CONSIDERATION": "train-second-step",
    "C. THE THIRD STEP IN THE PHENOMENOLOGICAL CONSIDERATION": "train-third-step",
    "INDEX": "index",
}

REPLACEMENTS = {
    "Phdinomenologie": "Phänomenologie",
    "Phiinomenologie": "Phänomenologie",
    "Phinomenologie": "Phänomenologie",
    "Phanomenoiogie": "Phänomenologie",
    "natiirliche Wissenschaften": "natürliche Wissenschaften",
    "Jiirgen Sander": "Jürgen Sander",
    "Seefelder Blatter": "Seefelder Blätter",
    "Di e Idee": "Die Idee",
    "EDMUND HUSSERL\nTHE IDEA OF PHENOMENOLOGY": "EDMUND HUSSERL\nTHE IDEA OF PHENOMENOLOGY",
    "SPRINGER-SCIENCE+BUSINESS MEDIA, B.V.": "SPRINGER-SCIENCE+BUSINESS MEDIA, B.V.",
    "positive Scientific investigations": "positive scientific investigations",
    "is-the phenomenological method": "is the phenomenological method",
    "therefore internally\nconsistent": "therefore internally\nconsistent",
    "meta- Physics": "metaphysics",
    "meta-physics": "metaphysics",
    "Selbstverstdndlichkeit": "Selbstverständlichkeit",
    "[reel/]": "[reell]",
    "[reel]": "[reell]",
    "[ree/l]": "[reell]",
    "/reell]": "[reell]",
    "(reel)": "[reell]",
    "aresult": "a result",
    "(10]": "[10]",
    "in tum": "in turn",
    "Ihave": "I have",
    "Ido": "I do",
    "1 may": "I may",
    "As a English translator": "As an English translator",
    "A new Science": "A new science",
    "The latter Sciences": "The latter sciences",
    "arbitrarily choosen": "arbitrarily chosen",
    "all the basics forms": "all the basic forms",
    "After the discovery of sphere": "After the discovery of the sphere",
    "—-": "—",
    "meta-Physics": "metaphysics",
    "extensionphenomenon": "extension-phenomenon",
    "{ntentional inexistence": "intentional inexistence",
    "Erklarung": "Erklärung",
    "Aufkldrung": "Aufklärung",
    "pet&Paors\neis &AAO ‘yévos": "μετάβασις εἰς ἄλλο γένος",
    "pet&Paors eis &AAO ‘yévos": "μετάβασις εἰς ἄλλο γένος",
    "pet&Paots eis &AAO ‘yévos": "μετάβασις εἰς ἄλλο γένος",
    "pet&Paots": "metabasis",
    "pet&Paors": "metabasis",
    "(pawOpevov": "φαινόμενον",
    "n't": "n't",
    "— Biologism": "- Biologism",
    "— to that end": "- to that end",
}

KEEP_LINEBREAK_HYPHEN_PREFIXES = {
    "anti",
    "co",
    "counter",
    "cross",
    "half",
    "house",
    "life",
    "meta",
    "non",
    "object",
    "pre",
    "red",
    "self",
    "so",
    "subject",
}


@dataclass
class Element:
    kind: str
    text: str
    ident: str | None = None
    page: int | None = None


@dataclass(frozen=True)
class Footnote:
    ident: str
    label: str
    text: str
    target: str
    section_id: str | None = None


FOOTNOTES = [
    Footnote(
        "intro-1",
        "1",
        "Karl Schuhmann, Husserl-Chronik: Denk- und Lebensweg Edmund Husserls. The Hague: Martinus Nijhoff, 1997, p. 74, my translation.",
        "master! Carpe diem.”",
        "translators-introduction",
    ),
    Footnote("intro-2", "2", "Husserl-Chronik, p. 77, my translation.", "No progress has been made.”", "translators-introduction"),
    Footnote("intro-3", "3", "Husserl-Chronik, p. 90, my translation.", "scientific significance.”", "translators-introduction"),
    Footnote("intro-4", "4", "Husserl-Chronik, p. 87, my translation.", "year in and year out.”", "translators-introduction"),
    Footnote("intro-5", "5", "Husserl-Chronik, p. 99, my translation.", "call myself a philosopher.”", "translators-introduction"),
    Footnote(
        "intro-6",
        "6",
        "Edited by Ulrich Claesges, Husserliana XVI, The Hague: Martinus Nijhoff, 1973.",
        "Ding und Raum: Vorlesungen 1907.",
        "translators-introduction",
    ),
    Footnote(
        "lecture-i-1",
        "1",
        "The numbers in brackets refer to the page numbers of the German edition in Husserliana II.",
        "[17]",
        "lecture-i",
    ),
    Footnote("lecture-i-2", "2", "See Addendum I.", "Thus far, however, we still stand on the ground of natural thinking.", "lecture-i"),
    Footnote("lecture-i-3", "3", "See Addendum II.", "to the level of fiction.", "lecture-i"),
    Footnote("lecture-ii-1", "1", "See Addendum III.", "What he lacks is wholly apparent.", "lecture-ii"),
    Footnote("train-1", "1", "In the manuscript “transcendent.”", "within this immanence is not immanent!", "train-third-step"),
]

FOREIGN_TERMS = [
    "Die Idee der Phänomenologie",
    "Idee der Phänomenologie",
    "Ding und Raum: Vorlesungen 1907",
    "Ding und Raum",
    "Dingkolleg",
    "Seefelder Blätter",
    "Husserl-Chronik: Denk- und Lebensweg Edmund Husserls",
    "Husserl-Chronik",
    "natürliche Wissenschaften",
    "positive Wissenschaften",
    "μετάβασις εἰς ἄλλο γένος",
    "φαινόμενον",
    "metabasis",
    "Selbstverständlichkeit",
    "Geistesleben",
    "Gegebenheiten",
    "Erklärung",
    "Aufklärung",
    "Erfahrung",
    "Triftigkeit",
    "gemeint",
    "Meinung",
    "Wissen",
    "Erkenntnis",
    "Bedeutung",
    "psychisch",
    "reellen",
    "reelles",
    "reeller",
    "reelle",
    "realen",
    "reale",
    "reell",
    "Sinn",
    "intentionale",
]


def ensure_ocr_cache(doc: fitz.Document) -> None:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    for index in range(doc.page_count):
        output = OCR_DIR / f"page-{index + 1:03d}.txt"
        if output.exists() and output.stat().st_size:
            continue
        image = PNG_DIR / f"page-{index + 1:03d}.png"
        if not image.exists():
            pix = doc[index].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
            pix.save(image)
        result = subprocess.run(
            ["tesseract", str(image), "stdout", "--psm", "6"],
            check=True,
            capture_output=True,
            text=True,
        )
        output.write_text(result.stdout, encoding="utf-8")


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\x0c", "")
    text = text.replace("LECTURE Ill", "LECTURE III")
    text = text.replace("Lecture Ill", "Lecture III")
    text = text.replace("Lecture N", "Lecture IV")
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"\n((?:\d+|['’‘*])\s+See Addendum)", r"\n\n\1", text)
    text = re.sub(r"\n(['’‘]\s+The numbers in brackets)", r"\n\n\1", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_running_furniture(text: str, pdf_index: int) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if lines and re.match(r"^\d+\s+THE IDEA OF PHENOMENOLOGY$", lines[0]):
        lines.pop(0)
    elif lines and re.match(r"^THE IDEA OF PHENOMENOLOGY\s+\d+$", lines[0]):
        lines.pop(0)
    elif lines and re.match(r"^TRANSLATOR[’']S INTRODUCTION\s+\d+$", lines[0]):
        lines.pop(0)
    elif lines and re.match(r"^LECTURE\s+[IVX]+\s+\d+$", lines[0]):
        lines.pop(0)
    elif lines and re.match(r"^ADDENDA\s+\d+$", lines[0]):
        lines.pop(0)
    elif lines and re.match(r"^THE TRAIN OF THOUGHT IN THE LECTURES\s+\d+$", lines[0]):
        lines.pop(0)

    if pdf_index not in {4} and lines and re.match(r"^\d{1,3}$", lines[-1].strip()):
        lines.pop()
    return "\n".join(lines).strip()


def join_wrapped_lines(lines: list[str]) -> str:
    output = ""
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if not output:
            output = line
            continue

        last_word = output.split()[-1] if output.split() else ""
        if output.endswith("-"):
            prefix = last_word[:-1].strip("“‘'\"(").lower()
            if prefix in KEEP_LINEBREAK_HYPHEN_PREFIXES:
                output += line
            else:
                output = output[:-1] + line
        else:
            output += " " + line
    return output


def split_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for chunk in re.split(r"\n\s*\n", text):
        lines = [line for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        paragraphs.append(clean_paragraph(normalize_text(join_wrapped_lines(lines))))
    return paragraphs


def clean_paragraph(text: str) -> str:
    text = re.sub(r"^TRANSLATOR[’']\s*S INTRODUCTION\s+\d+\s+", "", text)
    text = re.sub(r"^LECTURE\s+[|I1lV]+\s+\d+\s+", "", text)
    text = text.replace(".”' On November", ".” On November")
    text = text.replace("progress has been made.””", "progress has been made.”")
    text = text.replace("significance.”* Undeterred", "significance.” Undeterred")
    text = text.replace("philosopher.”* Thus", "philosopher.” Thus")
    text = text.replace("philosopher.”*", "philosopher.”")
    text = text.replace("[17]'", "[17]")
    text = text.replace("thinking.’", "thinking.")
    text = text.replace("fiction?’", "fiction.")
    text = text.replace("apparent.’ What", "apparent. What")
    if "Lee Hardy Calvin College ENDNOTES" in text:
        return "Lee Hardy\nCalvin College"
    return normalize_text(text)


def section_heading(text: str) -> tuple[str, str] | None:
    cleaned = re.sub(r"^\[\d+\]\s+", "", text.strip())
    upper = cleaned.upper().replace("’", "'")
    if upper in SECTION_IDS:
        return cleaned, SECTION_IDS[upper]
    return None


def page_to_elements(text: str, pdf_index: int) -> list[Element]:
    elements: list[Element] = []
    text = normalize_text(remove_running_furniture(normalize_text(text), pdf_index))

    if pdf_index == 2:
        lines = [line.strip() for line in text.splitlines() if line.strip() and line.strip() != "ON"]
        return [Element("title", "\n".join(lines), page=None)]

    if pdf_index == 4:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return [Element("toc", "\n".join(lines), ident="contents")]

    for paragraph in split_paragraphs(text):
        train_match = re.match(r"^\[3\]\s+(THE TRAIN OF THOUGHT IN THE LECTURES)\s+(.+)$", paragraph)
        if train_match:
            elements.append(Element("h2", train_match.group(1), SECTION_IDS[train_match.group(1)], 61))
            elements.append(Element("p", train_match.group(2), page=61))
            continue

        leading_heading = re.match(
            r"^((?:LECTURE [IVX]+)|(?:ADDENDUM [IVX]+)|(?:[ABC]\. THE [A-Z ]+ IN THE PHENOMENOLOGICAL CONSIDERATION))\s+(.+)$",
            paragraph,
        )
        if leading_heading and leading_heading.group(1).upper() in SECTION_IDS:
            heading_text = leading_heading.group(1)
            level = "h3" if heading_text.startswith(("A. ", "B. ", "C. ")) else "h2"
            elements.append(Element(level, heading_text, SECTION_IDS[heading_text.upper()], None))
            elements.append(Element("p", leading_heading.group(2), page=None))
            continue

        heading = section_heading(paragraph)
        if heading:
            level = "h3" if heading[0].startswith(("ADDENDUM", "A. ", "B. ", "C. ")) else "h2"
            elements.append(Element(level, heading[0], heading[1], None))
            continue

        elements.append(Element("p", paragraph, page=None))

    return elements


def image_for_page(doc: fitz.Document, pdf_index: int) -> Path:
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    image = PNG_DIR / f"page-{pdf_index + 1:03d}.png"
    if not image.exists():
        pix = doc[pdf_index].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        pix.save(image)
    return image


def index_lines_from_tsv(doc: fitz.Document, pdf_index: int) -> tuple[list[str], list[str]]:
    INDEX_TSV_DIR.mkdir(parents=True, exist_ok=True)
    tsv = INDEX_TSV_DIR / f"page-{pdf_index + 1:03d}.tsv"
    if not tsv.exists() or not tsv.stat().st_size:
        image = image_for_page(doc, pdf_index)
        result = subprocess.run(
            ["tesseract", str(image), "stdout", "--psm", "6", "tsv"],
            check=True,
            capture_output=True,
            text=True,
        )
        tsv.write_text(result.stdout, encoding="utf-8")

    rows = list(csv.DictReader(tsv.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        text = row.get("text", "").strip()
        if not text:
            continue
        if int(float(row.get("conf", "-1"))) < 0:
            continue
        key = (row["block_num"], row["par_num"], row["line_num"])
        grouped.setdefault(key, []).append(row)

    page_width = doc[pdf_index].rect.width * 3
    mid = page_width / 2
    left: list[tuple[int, str]] = []
    right: list[tuple[int, str]] = []
    for words in grouped.values():
        words = sorted(words, key=lambda row: int(row["left"]))
        for column_words, target in (
            ([word for word in words if int(word["left"]) < mid], left),
            ([word for word in words if int(word["left"]) >= mid], right),
        ):
            if not column_words:
                continue
            line_text = " ".join(word["text"] for word in column_words)
            line_text = normalize_index_line(line_text)
            if (
                not line_text
                or re.match(r"^\d{1,3}$", line_text)
                or "THE IDEA OF PHENOMENOLOGY" in line_text
                or line_text == "Index"
            ):
                continue
            y = min(int(word["top"]) for word in column_words)
            target.append((y, line_text))

    return [text for _, text in sorted(left)], [text for _, text in sorted(right)]


def normalize_index_line(text: str) -> str:
    text = normalize_text(text)
    text = text.replace("28—", "28-")
    text = text.replace("16--21", "16-21")
    text = text.replace("60--62", "60-62")
    text = text.replace("Ap~ces", "Appearances")
    text = re.sub(r"\s+,", ",", text)
    return text


def index_elements(doc: fitz.Document) -> list[Element]:
    elements = [Element("h2", "Index", "index", None)]
    left_70, right_70 = index_lines_from_tsv(doc, 70)
    left_71, right_71 = index_lines_from_tsv(doc, 71)
    columns = [
        "\n".join(join_index_lines(left_70 + left_71)),
        "\n".join(join_index_lines(right_70 + right_71)),
    ]
    return elements + [Element("index", "\n\n".join(columns), "index-text", None)]


def is_note_text(text: str) -> bool:
    return bool(re.match(r"^['’‘]?\s*(\d+|\*)\s+", text))


def is_extracted_note_text(text: str) -> bool:
    stripped = text.strip()
    return (
        stripped in {"2 See Addendum I.", "3 See Addendum II.", "' See Addendum III.", "’ See Addendum III.", "‘In the manuscript “transcendent.”"}
        or stripped.startswith("' The numbers in brackets refer to the page numbers")
        or stripped.startswith("’ The numbers in brackets refer to the page numbers")
    )


def drop_extracted_notes(elements: list[Element]) -> list[Element]:
    return [element for element in elements if element.kind != "p" or not is_extracted_note_text(element.text)]


def merge_continuations(elements: list[Element]) -> list[Element]:
    merged: list[Element] = []
    sentence_end = tuple(".?!:”’\"')]>")
    for element in elements:
        if (
            merged
            and element.kind == "p"
            and merged[-1].kind == "p"
            and not is_note_text(element.text)
            and not is_note_text(merged[-1].text)
        ):
            previous = merged[-1].text.rstrip()
            current = element.text.lstrip()
            if previous.endswith("-") and current[:1].islower():
                prefix = previous.split()[-1][:-1].strip("“‘'\"(").lower()
                if prefix in KEEP_LINEBREAK_HYPHEN_PREFIXES:
                    merged[-1].text = previous + current
                else:
                    merged[-1].text = previous[:-1] + current
                continue
            if not previous.endswith(sentence_end) and current[:1].islower():
                merged[-1].text = previous + " " + current
                continue
        merged.append(element)
    return merged


def emphasize_foreign_terms(escaped: str) -> str:
    placeholders: dict[str, str] = {}
    result = escaped
    for index, term in enumerate(sorted(FOREIGN_TERMS, key=len, reverse=True)):
        escaped_term = html.escape(term, quote=False)
        placeholder = f"@@FOREIGN_TERM_{index}@@"
        pattern = re.compile(rf"(?<![\w>-]){re.escape(escaped_term)}(?![\w<])")
        result = pattern.sub(placeholder, result)
        placeholders[placeholder] = f"<em>{escaped_term}</em>"
    for placeholder, replacement in placeholders.items():
        result = result.replace(placeholder, replacement)
    return result


def join_index_lines(lines: list[str]) -> list[str]:
    joined: list[str] = []
    for line in lines:
        if joined and joined[-1].endswith("-"):
            joined[-1] = joined[-1][:-1] + line
        elif joined and re.match(r"^\d", line):
            joined[-1] += " " + line
        elif joined and re.match(r"^(cal,|chological,|non of,|positive,|pure,|63-65,)", line):
            joined[-1] += " " + line
        else:
            joined.append(line)
    return joined


def title_html(text: str) -> str:
    lines = [emphasize_foreign_terms(html.escape(line)) for line in text.splitlines()]
    return (
        "<section class=\"title-page\" aria-labelledby=\"title\">\n"
        f"<p class=\"author\">{lines[0]}</p>\n"
        f"<h1 id=\"title\">{lines[1]}</h1>\n"
        f"<p>{lines[2]}<br>{lines[3]}<br>{lines[4]}</p>\n"
        f"<p class=\"credit\">{lines[5]}<br>{lines[6]}</p>\n"
        f"<p class=\"publisher\">{lines[-1]}</p>\n"
        "</section>"
    )


def footnote_popover(note: Footnote) -> str:
    note_text = emphasize_foreign_terms(html.escape(note.text, quote=False))
    return (
        '<span class="footnote-popover">'
        f'<sup id="fnref-{note.ident}" class="note-ref"><a href="#fn-{note.ident}">{html.escape(note.label)}</a></sup>'
        f'<span class="floating-note" id="sn-{note.ident}" role="note">'
        f'<span class="floating-note-number">{html.escape(note.label)}</span> {note_text}</span>'
        '</span>'
    )


def render_text_with_footnotes(text: str, section_id: str | None, inserted: set[str]) -> str:
    escaped = html.escape(text, quote=False).replace("\n", "<br>")
    if section_id is not None:
        for note in FOOTNOTES:
            if note.section_id != section_id or note.ident in inserted:
                continue
            target = html.escape(note.target, quote=False)
            idx = escaped.find(target)
            if idx == -1:
                continue
            end = idx + len(target)
            escaped = escaped[:end] + footnote_popover(note) + escaped[end:]
            inserted.add(note.ident)
    return emphasize_foreign_terms(escaped)


def footnotes_html() -> str:
    items = []
    for note in FOOTNOTES:
        note_text = emphasize_foreign_terms(html.escape(note.text, quote=False))
        items.append(
            f'<li id="fn-{note.ident}"><span class="footnote-list-number">{html.escape(note.label)}.</span> '
            f'{note_text} <a class="backref" href="#fnref-{note.ident}">↩</a></li>'
        )
    return (
        '<section class="footnotes" aria-labelledby="footnotes">'
        '<h2 id="footnotes">Footnotes</h2>'
        '<ol>'
        + "\n".join(items)
        + '</ol></section>'
    )


def render(elements: list[Element]) -> str:
    body: list[str] = []
    headings: list[Heading] = [Heading(2, "Title", "title")]
    current_section: str | None = None
    inserted_footnotes: set[str] = set()
    for element in elements:
        if element.kind == "title":
            body.append(title_html(element.text))
        elif element.kind == "toc":
            headings.append(Heading(2, "Contents", "contents"))
        elif element.kind in {"h2", "h3"}:
            tag = element.kind
            ident = f' id="{element.ident}"' if element.ident else ""
            if element.ident:
                current_section = element.ident
                headings.append(Heading(2 if tag == "h2" else 3, element.text, element.ident))
            body.append(f"<{tag}{ident}>{html.escape(element.text)}</{tag}>")
        elif element.kind == "index":
            left, right = element.text.split("\n\n", 1)
            body.append(
                '<div class="index-columns">'
                f"<pre>{html.escape(left)}</pre>"
                f"<pre>{html.escape(right)}</pre>"
                "</div>"
            )
        elif element.kind == "p":
            if is_extracted_note_text(element.text):
                continue
            rendered = render_text_with_footnotes(element.text, current_section, inserted_footnotes)
            body.append(f"<p>{rendered}</p>")
    missing = [note.ident for note in FOOTNOTES if note.ident not in inserted_footnotes]
    if missing:
        raise RuntimeError(f"Could not place footnotes: {', '.join(missing)}")
    body.insert(1, render_linked_contents(headings, title="Table of Contents"))
    body.append(footnotes_html())
    return wrap_html_document(
        "The Idea of Phenomenology",
        "\n".join(body),
        render_sublime_nav(headings),
        css=SUBLIME_BOOK_CSS + "\n.index-columns{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:18px}\n.index-columns pre{white-space:pre-wrap;margin:0;font:0.88rem/1.35 Georgia,'Times New Roman',serif}\n.note{font-size:.92rem;color:#39342f;margin-top:-.35rem}\n@media (max-width:680px){.index-columns{grid-template-columns:1fr}}",
        script=HTML_SCRIPT,
    )


HTML_SCRIPT = """
(() => {
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const closeLater = (wrap) => {
    clearTimeout(wrap._noteTimer);
    wrap._noteTimer = setTimeout(() => wrap.classList.remove('is-open'), 120);
  };
  document.querySelectorAll('.footnote-popover').forEach((wrap) => {
    const ref = wrap.querySelector('.note-ref');
    const note = wrap.querySelector('.floating-note');
    const open = (event) => {
      clearTimeout(wrap._noteTimer);
      wrap.classList.add('is-open');
      note.style.visibility = 'hidden';
      note.style.display = 'block';
      const width = note.offsetWidth || 360;
      const height = note.offsetHeight || 120;
      const source = event.type.startsWith('focus') ? ref.getBoundingClientRect() : null;
      const x = source ? source.left : event.clientX;
      const y = source ? source.bottom : event.clientY;
      const left = clamp(x - 16, 12, window.innerWidth - width - 12);
      const top = clamp(y + 14, 12, window.innerHeight - height - 12);
      note.style.setProperty('--note-left', `${left}px`);
      note.style.setProperty('--note-top', `${top}px`);
      note.style.visibility = '';
      note.style.display = '';
    };
    ref.addEventListener('mouseenter', open);
    ref.addEventListener('focusin', open);
    ref.addEventListener('mouseleave', () => closeLater(wrap));
    ref.addEventListener('focusout', () => closeLater(wrap));
    note.addEventListener('mouseenter', () => { clearTimeout(wrap._noteTimer); wrap.classList.add('is-open'); });
    note.addEventListener('mouseleave', () => closeLater(wrap));
  });
})();
"""


def main() -> None:
    doc = fitz.open(PDF_PATH)
    ensure_ocr_cache(doc)
    elements: list[Element] = []
    for pdf_index in range(doc.page_count):
        if pdf_index in OMIT_PAGES or pdf_index in INDEX_PAGES:
            continue
        text = (OCR_DIR / f"page-{pdf_index + 1:03d}.txt").read_text(encoding="utf-8")
        elements.extend(page_to_elements(text, pdf_index))
    elements = drop_extracted_notes(elements)
    elements = merge_continuations(elements)
    elements.extend(index_elements(doc))
    OUTPUT_PATH.write_text(render(elements), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
