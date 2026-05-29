from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


for dep_dir in (Path(".codex_deps"), Path("../sublime-object-of-ideaology/.codex_deps")):
    if dep_dir.exists():
        sys.path.insert(0, str(dep_dir))

try:
    import fitz  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "PyMuPDF is required. Install it with `python3 -m pip install --target .codex_deps pymupdf`."
    ) from exc


PDF_PATH = Path("Enjoy Your Symptom!_ Jacques Lacan in Hollywood and Out.pdf")
OUTPUT_PATH = Path("enjoy-your-symptom.html")
EPUB_PATH = next(iter(Path(".").glob("*.epub")), None)
FIGURE_DIR = Path("assets/figures")


BODY_RANGES = [
    ("preface-classics", 7, 13),
    ("introduction", 15, 16),
    ("ch1", 18, 33),
    ("ch2", 38, 58),
    ("ch3", 64, 89),
    ("ch4", 94, 113),
    ("ch5", 118, 144),
    ("ch6", 149, 175),
]

NOTE_RANGES = {
    "preface-classics": (14, 14),
    "ch1": (33, 36),
    "ch2": (58, 63),
    "ch3": (90, 93),
    "ch4": (113, 117),
    "ch5": (144, 148),
    "ch6": (175, 176),
}

FIGURES_BY_PAGE = {
    50: [
        ("page56_01.jpg", "Lacanian diagram of objet a interrupting the circle of pleasure"),
    ],
    69: [
        ("page89_01.jpg", "Lacanian Venn diagram of the subject, objet a, and the signifying chain"),
        ("page88_01.jpg", "Lacanian Venn diagram of the subject, objet a, and the signifying chain"),
    ],
    72: [
        ("page93_01.jpg", "Diagram contrasting historicity, historicism, nostalgia, and repetition"),
    ],
    83: [
        ("page111_01.jpg", "Diagram of objet a between personal description and teaching"),
    ],
    96: [
        ("page132_01.jpg", "Two stills illustrating the distorted face and mask"),
    ],
    112: [
        ("page159_01.jpg", "Facial portrait before distortion"),
        ("page160_01.jpg", "Facial portrait after distortion"),
    ],
}

CONTENTS = [
    ("Preface to the Routledge Classics Edition", "preface-to-the-routledge-classics-edition"),
    ("Introduction to the New Revised Edition", "introduction-to-the-new-revised-edition"),
    ("Introduction", "introduction"),
    ("1 Why Does a Letter Always Arrive at Its Destination?", "1-why-does-a-letter-always-arrive-at-its-destination"),
    ("1.1 Death and Sublimation: The Final Scene of City Lights", "1-1-death-and-sublimation-the-final-scene-of-city-lights"),
    ("1.2 Imaginary, Symbolic, Real", "1-2-imaginary-symbolic-real"),
    ("2 Why is Woman a Symptom of Man?", "2-why-is-woman-a-symptom-of-man"),
    ("2.1 Why is Suicide the Only Successful Act?", "2-1-why-is-suicide-the-only-successful-act"),
    ("2.2 The Night of the World", "2-2-the-night-of-the-world"),
    ("3 Why is Every Act a Repetition?", "3-why-is-every-act-a-repetition"),
    ("3.1 Beyond Distributive Justice", "3-1-beyond-distributive-justice"),
    ("3.2 Identity and Authority", "3-2-identity-and-authority"),
    ("4 Why Does the Phallus Appear?", "4-why-does-the-phallus-appear"),
    ("4.1 Grimaces of the Real", "4-1-grimaces-of-the-real"),
    ("4.2 Phallophany of the Anal Father", "4-2-phallophany-of-the-anal-father"),
    ("5 Why Are There Always Two Fathers?", "5-why-are-there-always-two-fathers"),
    ("5.1 At the Origins of Noir: The Humiliated Father", "5-1-at-the-origins-of-noir-the-humiliated-father"),
    ("5.2 Die Versagung", "5-2-die-versagung"),
    ("6 Why is Reality Always Multiple?", "6-why-is-reality-always-multiple"),
    ("6.1 Is There a Proper Way to Remake a Hitchcock Film?", "6-1-is-there-a-proper-way-to-remake-a-hitchcock-film"),
    ("6.2 The Matrix, Or the Two Sides of Perversion", "6-2-the-matrix-or-the-two-sides-of-perversion"),
    ("Index", "index"),
]

TEXT_REPLACEMENTS = {
    "replusive": "repulsive",
    "replusion": "repulsion",
    "de Quniceyian": "de Quinceyian",
    "Englightenment": "Enlightenment",
    "presisely": "precisely",
    "accidently": "accidentally",
    "unbeknowst": "unbeknownst",
    "ninteenth": "nineteenth",
    "épmigrée": "émigrée",
    "ressemblance": "resemblance",
    "notorius": "notorious",
    "stimatized": "stigmatized",
    "selfincurred": "self-incurred",
    "Descrates": "Descartes",
    "catastrophy": "catastrophe",
    "indiscernable": "indiscernible",
    " rucial": " crucial",
    "ressembles": "resembles",
    "more tham": "more than",
    "non- ideological": "non-ideological",
    "Post- modernism": "Postmodernism",
    "hard- boiled": "hard-boiled",
    "movement image”to": "movement image” to",
    "Story-teller,”in": "Story-teller,” in",
    "Awry:An": "Awry: An",
    "Subject:Film": "Subject: Film",
    "MA:MIT": "MA: MIT",
    "MA.:": "MA:",
    "Vienna:Hora": "Vienna: Hora",
    "Idealogy": "Ideology",
    "Kripe": "Kripke",
    "Laciau": "Laclau",
    "Vonnegur": "Vonnegut",
    "Yogimbo": "Yojimbo",
    "Rotham": "Rothman",
    "Edgar Allen": "Edgar Allan",
    "Truffauts’": "Truffaut’s",
    "psychoanalyse": "psychanalyse",
    "van:Psycho": "van: Psycho",
    "165n28;Jacob": "165n28; Jacob",
    "L’lmage-mouvement": "L’Image-mouvement",
    "sublime:the": "sublime: the",
    "Mass.": "MA",
    "Paris:Editions": "Paris: Editions",
    "London:Tavistock": "London: Tavistock",
    "“phantom of the opera“": "“phantom of the opera”",
    "Kierkegaard’s materialist r": "Kierkegaard’s materialist reversal of Hegel",
    "Kurowasa": "Kurosawa",
    "Deiter": "Dieter",
    "vo. 9": "vol. 9",
    "Barrons Educational": "Barron's Educational",
    "Hitchcock Centenary Conference organized by NYU, October 12–17, 1999.": (
        "Hitchcock Centenary Conference organized by NYU, October 12-17, 1999."
    ),
}


@dataclass
class Heading:
    level: int
    text: str
    ident: str


@dataclass
class ConvertState:
    note_refs: list[tuple[str, str, str]]
    missing_notes: list[str]
    headings: list[Heading]
    used_ids: dict[str, int]


def clean_spaces(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\x0c", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    text = re.sub(r"([([{])\s+", r"\1", text)
    text = re.sub(r"\s+([])}])", r"\1", text)
    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"\bC+c+rucial\b", "Crucial", text)
    text = re.sub(r"\bc+c+rucial\b", "crucial", text)
    return text.strip()


def apply_replacements_markup(markup: str) -> str:
    for source, target in TEXT_REPLACEMENTS.items():
        markup = markup.replace(html.escape(source, quote=False), html.escape(target, quote=False))
        markup = markup.replace(source, target)
    markup = re.sub(r"\bC+c+rucial\b", "Crucial", markup)
    markup = re.sub(r"\bc+c+rucial\b", "crucial", markup)
    return markup


def slugify(text: str, used: dict[str, int]) -> str:
    value = html.unescape(text).lower()
    value = value.replace("ž", "z").replace("’", "").replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value:
        value = "section"
    base = value
    count = used.get(base, 0)
    used[base] = count + 1
    if count:
        value = f"{base}-{count + 1}"
    return value


def block_text(block: dict) -> str:
    lines = []
    for line in block.get("lines", []):
        lines.append("".join(span["text"] for span in line.get("spans", [])))
    return clean_spaces(" ".join(lines))


def extract_epub_image(filename: str) -> Path | None:
    if EPUB_PATH is None:
        return None
    source = f"OPS/images/{filename}"
    with ZipFile(EPUB_PATH) as z:
        try:
            data = z.read(source)
        except KeyError:
            return None
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    target = FIGURE_DIR / filename
    if not target.exists() or target.read_bytes() != data:
        target.write_bytes(data)
    return target


def figure_html(page_index: int, sequence: int) -> str:
    figure = FIGURES_BY_PAGE.get(page_index, [])
    if sequence >= len(figure):
        return ""
    filename, alt = figure[sequence]
    path = extract_epub_image(filename)
    if path is None:
        return ""
    return (
        f'<figure class="book-figure"><img src="{html.escape(path.as_posix(), quote=True)}" '
        f'alt="{html.escape(alt, quote=True)}" loading="lazy" decoding="async"></figure>'
    )


def block_max_size(block: dict) -> float:
    sizes = [
        span["size"]
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        if span.get("text")
    ]
    return max(sizes, default=0.0)


def is_note_heading(block: dict) -> bool:
    return block_text(block) == "NOTES"


def is_sup_note_span(span: dict) -> bool:
    text = span.get("text", "").strip()
    return bool(re.fullmatch(r"\d{1,2}", text)) and span.get("size", 99) <= 9.5 and bool(span.get("flags", 0) & 1)


def span_html(span: dict, note_section: str | None, notes: dict[str, dict[str, str]], state: ConvertState) -> str:
    text = span.get("text", "")
    if not text:
        return ""
    stripped = text.strip()
    flags = span.get("flags", 0)
    size = span.get("size", 99)

    if note_section and is_sup_note_span(span):
        note_html = notes.get(note_section, {}).get(stripped)
        ident = f"{note_section}-{stripped}"
        if note_html is None:
            state.missing_notes.append(ident)
            return f'<sup class="note-ref missing-note">{html.escape(stripped)}</sup>'
        state.note_refs.append((ident, stripped, note_html))
        return (
            f'<span class="footnote-popover"><sup id="fnref-{ident}" class="note-ref">'
            f'<a href="#fn-{ident}">{html.escape(stripped)}</a></sup>'
            f'<span class="floating-note" id="sn-{ident}" role="note">'
            f'<span class="floating-note-number">{html.escape(stripped)}</span> {note_html}</span></span>'
        )

    escaped = html.escape(text, quote=False)
    if size <= 9.5 and re.fullmatch(r"\d{1,2}", stripped) and not (flags & 1):
        return f"<sub>{html.escape(stripped)}</sub>"
    if flags & 2:
        return f"<em>{escaped}</em>"
    if flags & 16 and size >= 13:
        return f"<strong>{escaped}</strong>"
    return escaped


def join_line_html(lines: list[tuple[str, str]]) -> str:
    result = ""
    prev_plain = ""
    for plain, markup in lines:
        plain = plain.strip()
        markup = markup.strip()
        if not markup:
            continue
        if not result:
            result = markup
        elif prev_plain.endswith("-"):
            result += markup
        else:
            result += " " + markup
        prev_plain = plain
    return apply_replacements_markup(clean_spaces(result))


def block_inline_html(
    block: dict,
    note_section: str | None,
    notes: dict[str, dict[str, str]],
    state: ConvertState,
) -> str:
    lines: list[tuple[str, str]] = []
    for line in block.get("lines", []):
        line_plain = "".join(span["text"] for span in line.get("spans", []))
        line_markup = "".join(span_html(span, note_section, notes, state) for span in line.get("spans", []))
        lines.append((line_plain, line_markup))
    return join_line_html(lines)


def note_line_html(line: dict) -> tuple[str | None, str]:
    spans = [dict(span) for span in line.get("spans", [])]
    if not spans:
        return None, ""
    label = None
    first = spans[0].get("text", "")
    match = re.match(r"^\s*(\d{1,2})\s+", first)
    if match:
        label = match.group(1)
        spans[0]["text"] = first[match.end() :]
    elif re.fullmatch(r"\s*\d{1,2}\s*", first) and len(spans) > 1 and spans[1].get("text", "").startswith(" "):
        label = first.strip()
        spans[0]["text"] = ""
        spans[1]["text"] = spans[1].get("text", "").lstrip()
    plain = "".join(span.get("text", "") for span in spans)
    parts = []
    for span in spans:
        text = span.get("text", "")
        if not text:
            continue
        escaped = html.escape(text, quote=False)
        if span.get("flags", 0) & 2:
            escaped = f"<em>{escaped}</em>"
        parts.append(escaped)
    return label, join_line_html([(plain, "".join(parts))])


def parse_notes(doc: fitz.Document) -> dict[str, dict[str, str]]:
    all_notes: dict[str, dict[str, str]] = {}
    for section, (start, end) in NOTE_RANGES.items():
        notes: dict[str, str] = {}
        current_label: str | None = None
        current_lines: list[str] = []
        note_start_y: float | None = None
        for page_index in range(start, end + 1):
            page = doc[page_index]
            blocks = sorted(
                [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0],
                key=lambda b: (b["bbox"][1], b["bbox"][0]),
            )
            if page_index == start:
                for block in blocks:
                    if is_note_heading(block):
                        note_start_y = block["bbox"][3]
                        break
                if note_start_y is None and section != "ch3":
                    note_start_y = 0
            else:
                note_start_y = 0
            for block in blocks:
                if note_start_y is not None and block["bbox"][1] < note_start_y:
                    continue
                if is_note_heading(block):
                    continue
                for line in block.get("lines", []):
                    label, markup = note_line_html(line)
                    if not markup:
                        continue
                    if label is not None:
                        if current_label is not None:
                            notes[current_label] = clean_spaces(" ".join(current_lines))
                        current_label = label
                        current_lines = [markup]
                    elif current_label is not None:
                        current_lines.append(markup)
        if current_label is not None:
            notes[current_label] = clean_spaces(" ".join(current_lines))
        all_notes[section] = {label: apply_replacements_markup(text) for label, text in notes.items()}
    return all_notes


def add_heading(level: int, text: str, state: ConvertState) -> str:
    text = clean_spaces(text)
    ident = slugify(text, state.used_ids)
    state.headings.append(Heading(level, text, ident))
    return f'<h{level} id="{ident}">{html.escape(text, quote=False)}</h{level}>'


def titlecase_section(text: str) -> str:
    text = clean_spaces(text).title()
    for word in ("And", "Or", "The", "Of", "To", "In", "At", "A", "An", "Is"):
        text = re.sub(rf"(?<!^)\b{word}\b", word.lower(), text)
    text = re.sub(r"^(\d\.\d\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    text = re.sub(r":\s+([a-z])", lambda m: ": " + m.group(1).upper(), text)
    text = text.replace(", or ", ", Or ")
    text = text.replace(" Or the ", " Or the ")
    text = text.replace("Lacan", "Lacan").replace("Hitchcock", "Hitchcock")
    return text


def title_page() -> str:
    return """<section class="title-page" aria-labelledby="title">
<p class="author">Slavoj Žižek</p>
<h1 id="title">Enjoy Your Symptom!</h1>
<p class="subtitle">Jacques Lacan in Hollywood and Out</p>
<p>With a new preface by the author</p>
</section>"""


def contents_html() -> str:
    rows = []
    for title, target in CONTENTS:
        rows.append(f'<li><a href="#{target}">{html.escape(title, quote=False)}</a></li>')
    return '<section aria-labelledby="contents"><h2 id="contents">Contents</h2>\n<ol class="contents">\n' + "\n".join(rows) + "\n</ol></section>"


def classify_heading(blocks: list[dict], index: int) -> tuple[str | None, int]:
    block = blocks[index]
    text = block_text(block)
    size = block_max_size(block)
    if size >= 22 and re.fullmatch(r"\d", text):
        parts = [text]
        consumed = 1
        for next_block in blocks[index + 1 :]:
            next_text = block_text(next_block)
            next_size = block_max_size(next_block)
            if next_size >= 16 and next_text.upper() == next_text and not re.match(r"^\d\.\d", next_text):
                parts.append(next_text)
                consumed += 1
                continue
            break
        return "h2:" + " ".join(parts), consumed
    if size >= 16 and re.match(r"^\d\.\d\s+", text):
        parts = [text]
        consumed = 1
        for next_block in blocks[index + 1 :]:
            next_text = block_text(next_block)
            next_size = block_max_size(next_block)
            if next_size >= 16 and next_text.upper() == next_text and not re.match(r"^\d\.\d", next_text):
                parts.append(next_text)
                consumed += 1
                continue
            break
        return "h3:" + " ".join(parts), consumed
    if size >= 16:
        if text in {"PREFACE TO THE ROUTLEDGE CLASSICS EDITION", "INTRODUCTION TO THE NEW REVISED EDITION", "INTRODUCTION"}:
            return "h2:" + text, 1
        return "h4:" + text, 1
    return None, 0


def extract_body(doc: fitz.Document, notes: dict[str, dict[str, str]], state: ConvertState) -> list[str]:
    out: list[str] = [title_page(), contents_html()]
    for section, start, end in BODY_RANGES:
        for page_index in range(start, end + 1):
            page = doc[page_index]
            blocks = sorted(
                [b for b in page.get_text("dict")["blocks"] if b.get("type") in {0, 1}],
                key=lambda b: (b["bbox"][1], b["bbox"][0]),
            )
            usable: list[dict] = []
            figure_count = 0
            for block in blocks:
                if block.get("type") == 0:
                    if is_note_heading(block):
                        break
                    if not block_text(block):
                        continue
                    usable.append(block)
                elif block.get("type") == 1 and page_index in FIGURES_BY_PAGE:
                    block = dict(block)
                    block["_figure_sequence"] = figure_count
                    figure_count += 1
                    if block["_figure_sequence"] < len(FIGURES_BY_PAGE[page_index]):
                        usable.append(block)

            i = 0
            while i < len(usable):
                if usable[i].get("type") == 1:
                    figure = figure_html(page_index, usable[i]["_figure_sequence"])
                    if figure:
                        out.append(figure)
                    i += 1
                    continue
                heading, consumed = classify_heading(usable, i)
                if heading:
                    level_text, text = heading.split(":", 1)
                    level = int(level_text[1])
                    out.append(add_heading(level, titlecase_section(text) if re.match(r"^\d\.\d", text) else text, state))
                    i += consumed
                    continue

                block = usable[i]
                plain = block_text(block)
                if plain in {"1", "2", "3"} and block["bbox"][0] < 90:
                    out.append(f'<p class="section-number">{html.escape(plain)}</p>')
                    i += 1
                    continue
                text = block_inline_html(block, section if section in notes else None, notes, state)
                if text:
                    css = ' class="inset"' if block["bbox"][0] >= 90 else ""
                    out.append(f"<p{css}>{text}</p>")
                i += 1
    return out


def extract_index(doc: fitz.Document, state: ConvertState) -> str:
    if EPUB_PATH is not None:
        epub_index = extract_epub_index(state)
        if epub_index:
            return epub_index

    lines: list[str] = []
    for page_index in range(177, 190):
        page = doc[page_index]
        blocks = sorted(
            [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0],
            key=lambda b: (b["bbox"][1], b["bbox"][0]),
        )
        for block in blocks:
            text = block_text(block)
            if not text or text == "INDEX":
                continue
            if text.startswith("Page references to footnotes"):
                lines.append("")
                lines.append(text)
                lines.append("")
                continue
            for line in block.get("lines", []):
                line_text = clean_spaces("".join(span["text"] for span in line.get("spans", [])))
                if line_text:
                    lines.append(line_text)
    ident = slugify("Index", state.used_ids)
    state.headings.append(Heading(2, "Index", ident))
    escaped = html.escape("\n".join(lines).strip(), quote=False)
    return f'<h2 id="{ident}">Index</h2>\n<div class="index-columns"><pre>{escaped}</pre></div>'


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def element_markup(node: ET.Element) -> str:
    parts = [html.escape(node.text or "", quote=False)]
    for child in list(node):
        child_text = element_markup(child)
        if local_name(child.tag) in {"i", "em"}:
            parts.append(f"<em>{child_text}</em>")
        elif local_name(child.tag) == "br":
            parts.append("<br>")
        else:
            parts.append(child_text)
        parts.append(html.escape(child.tail or "", quote=False))
    return apply_replacements_markup(clean_spaces("".join(parts)))


def extract_epub_index(state: ConvertState) -> str | None:
    assert EPUB_PATH is not None
    with ZipFile(EPUB_PATH) as z:
        try:
            source = z.read("OPS/xhtml/16_Index.xhtml")
        except KeyError:
            return None
    root = ET.fromstring(source)
    body = next((node for node in root.iter() if local_name(node.tag) == "body"), None)
    if body is None:
        return None
    ident = slugify("Index", state.used_ids)
    state.headings.append(Heading(2, "Index", ident))
    rows = []
    for node in body:
        if local_name(node.tag) != "p":
            continue
        cls = node.attrib.get("class", "")
        if cls == "headx":
            continue
        if cls == "indext":
            rows.append(f'<p class="index-note">{element_markup(node)}</p>')
        elif cls in {"index", "inde"}:
            rows.append(f'<p class="index-entry">{element_markup(node)}</p>')
    if not rows:
        return None
    return f'<h2 id="{ident}">Index</h2>\n<div class="index-list">\n' + "\n".join(rows) + "\n</div>"


def repair_inline_symbols(markup: str) -> str:
    return markup.replace(
        "S(</p>\n<p>), the signifier of the barred Other.",
        'S(<span class="math-symbol" aria-label="barred A">Ⱥ</span>), the signifier of the barred Other.',
    )


def footnotes_html(state: ConvertState) -> str:
    seen: set[str] = set()
    items = []
    for ident, label, note_html in state.note_refs:
        if ident in seen:
            continue
        seen.add(ident)
        items.append(
            f'<li id="fn-{ident}"><span class="footnote-list-number">{html.escape(label)}.</span> '
            f'{note_html} <a class="backref" href="#fnref-{ident}">↩</a></li>'
        )
    return '<section class="footnotes" aria-labelledby="footnotes"><h2 id="footnotes">Footnotes</h2><ol>\n' + "\n".join(items) + "\n</ol></section>"


def nav_html(headings: list[Heading]) -> str:
    items = ['<li><a class="nav-level-2" href="#title">Title</a></li>', '<li><a class="nav-level-2" href="#contents">Contents</a></li>']
    for heading in headings:
        if heading.level <= 4:
            items.append(
                f'<li><a class="nav-level-{heading.level}" href="#{heading.ident}">{html.escape(heading.text, quote=False)}</a></li>'
            )
    return '<nav class="page-nav" aria-label="Book navigation"><p>Navigate</p><ol>' + "\n".join(items) + "</ol></nav>"


STYLE = r"""
:root{color-scheme:light;--paper:#fffdf9;--ink:#171717;--muted:#655f56;--line:#ded5c8;--nav:#f0ece4;--accent:#7a3d00}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:#f6f1e9;color:var(--ink);font-family:Georgia,"Times New Roman",serif;line-height:1.58}
main{max-width:800px;margin:0 auto;padding:50px 28px 88px;background:var(--paper);min-height:100vh}
.page-nav{position:fixed;inset:0 auto 0 0;width:286px;padding:28px 20px;background:var(--nav);border-right:1px solid var(--line);overflow:auto}
.page-nav p{margin:0 0 16px;font:700 .76rem/1.2 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.page-nav ol{list-style:none;margin:0;padding:0}
.page-nav li{margin:0 0 3px}
.page-nav a{display:block;padding:3px 0;color:#38322c;text-decoration:none;font-size:.84rem;line-height:1.25}
.page-nav a:hover,.page-nav a:focus{text-decoration:underline;text-underline-offset:3px}
.nav-level-3{padding-left:14px!important}
.nav-level-4{padding-left:28px!important;color:#5d554b!important;font-size:.79rem!important}
h1,h2,h3,h4{line-height:1.18}
h1{font-size:2.45rem;text-align:center;margin:14px 0 12px;letter-spacing:.02em}
h2{font-size:1.5rem;text-align:center;margin:56px 0 24px;text-transform:uppercase}
h3{font-size:1.1rem;text-align:center;margin:38px 0 18px;text-transform:uppercase}
h4{font-size:1rem;text-align:left;margin:30px 0 13px}
p{font-size:1.02rem;margin:0 0 1rem}
p.inset{margin-left:1.7rem}
p.section-number{text-align:center;margin:1.6rem 0 1rem;font-size:1.05rem}
em{font-style:italic}
sub{font-size:.72em;line-height:0}
sup{font-size:.72em;line-height:0}
.title-page{text-align:center;min-height:78vh;display:flex;flex-direction:column;justify-content:center}
.title-page p{font-size:1.04rem}
.author{font-size:1.16rem;letter-spacing:.08em;text-transform:uppercase}
.subtitle{font-size:1.22rem;margin-top:0}
.contents{max-width:620px;margin:0 auto 44px;padding:0;list-style:none}
.contents li{border-bottom:1px dotted #b8afa3}
.contents a{display:block;padding:5px 0;color:#28231f;text-decoration:none}
.contents a:hover,.contents a:focus{text-decoration:underline;text-underline-offset:3px}
.footnote-popover{display:inline;position:relative}
.note-ref a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(122,61,0,.35);cursor:help}
.floating-note{position:fixed;left:var(--note-left,0);top:var(--note-top,0);z-index:20;display:none;width:min(390px,calc(100vw - 32px));max-height:min(48vh,390px);overflow:auto;padding:10px 12px 11px;border:1px solid #d8c7a8;border-radius:3px;background:#fffdf8;box-shadow:0 8px 24px rgba(0,0,0,.16);font-size:.82rem;line-height:1.4;color:#4f493f;user-select:text;text-align:left}
.floating-note-number,.footnote-list-number{font-weight:700;color:var(--accent)}
.footnote-popover.is-open .floating-note,.footnote-popover:focus-within .floating-note{display:block}
.footnotes{border-top:1px solid #ccc;margin-top:42px;padding-top:18px;font-size:.92rem}
.footnotes li{margin:.45rem 0}
.backref{text-decoration:none;margin-left:.35em}
.index-columns{margin-top:18px}
.index-columns pre{white-space:pre-wrap;margin:0;font:.88rem/1.38 Georgia,"Times New Roman",serif}
.index-list{margin-top:18px}
.index-note{font-size:.9rem;color:var(--muted)}
.index-entry{font-size:.9rem;line-height:1.38;margin:0 0 .28rem}
.book-figure{margin:24px auto 26px;text-align:center}
.book-figure img{display:block;max-width:min(100%,520px);height:auto;margin:0 auto}
.math-symbol{font-style:italic}
@media (min-width:1240px){body{padding-left:286px}.footnotes{display:none}}
@media (max-width:1239px){.page-nav{display:none}}
@media (min-width:681px) and (max-width:1239px){.footnotes{display:none}}
@media (max-width:680px){main{padding:32px 18px 64px}h1{font-size:2rem}h2{font-size:1.28rem}.floating-note{display:none}.footnotes{display:block}p.inset{margin-left:0}}
"""


SCRIPT = r"""
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
      const width = note.offsetWidth || 390;
      const height = note.offsetHeight || 140;
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


def build_html() -> str:
    doc = fitz.open(PDF_PATH)
    notes = parse_notes(doc)
    state = ConvertState(note_refs=[], missing_notes=[], headings=[], used_ids={})
    body = extract_body(doc, notes, state)
    body.append(extract_index(doc, state))
    body.append(footnotes_html(state))
    if state.missing_notes:
        missing = ", ".join(state.missing_notes)
        raise RuntimeError(f"Missing note text for: {missing}")
    body_html = repair_inline_symbols(chr(10).join(body))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Enjoy Your Symptom!</title>
<style>{STYLE}</style>
</head>
<body>
{nav_html(state.headings)}
<main>
{body_html}
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""


def main() -> None:
    OUTPUT_PATH.write_text(build_html(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
