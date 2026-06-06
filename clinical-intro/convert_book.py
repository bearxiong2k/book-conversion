from __future__ import annotations

import html
import posixpath
import re
import shutil
import subprocess
import sys
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, "../.codex_deps")
sys.path.insert(0, "..")

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning  # type: ignore
import fitz  # type: ignore

from book_conversion_toolkit import (
    Heading,
    STANDARD_BOOK_CSS,
    image_file_to_data_uri,
    render_linked_contents,
    render_standard_nav,
    wrap_html_document,
)


PDF_PATH = Path("A Clinical Introduction to Lacanian Psychoanalysis_ Theory.pdf")
EPUB_PATH = Path("A Clinical Introduction to Lacanian Psychoanalysis_ Theory.epub")
OUTPUT_PATH = Path("a-clinical-introduction-to-lacanian-psychoanalysis.html")
ASSET_DIR = Path("assets")
FIGURE_DIR = ASSET_DIR / "figures"


@dataclass(frozen=True)
class Line:
    page: int
    y: float
    x0: float
    x1: float
    text: str


@dataclass(frozen=True)
class Figure:
    page: int
    y: float
    src: str
    caption: str
    alt: str


@dataclass
class Element:
    kind: str
    text: str = ""
    ident: str | None = None
    level: int | None = None
    src: str | None = None
    alt: str | None = None
    caption: str | None = None


SECTION_STARTS: dict[int, list[Element]] = {
    2: [Element("heading", "Preface", "preface", 2)],
    6: [
        Element("part", "I. Desire and Psychoanalytic Technique", "part-i", 1),
        Element("heading", "1. Desire in Analysis", "chapter-1-desire-in-analysis", 2),
    ],
    15: [Element("heading", "2. Engaging the Patient in the Therapeutic Process", "chapter-2-engaging-the-patient", 2)],
    34: [Element("heading", "3. The Analytic Relationship", "chapter-3-the-analytic-relationship", 2)],
    50: [Element("heading", "4. Interpretation: Opening Up the Space of Desire", "chapter-4-opening-up-the-space-of-desire", 2)],
    59: [Element("heading", "5. The Dialectic of Desire", "chapter-5-the-dialectic-of-desire", 2)],
    84: [
        Element("part", "II. Diagnosis and the Positioning of the Analyst", "part-ii", 1),
        Element("heading", "6. A Lacanian Approach to Diagnosis", "chapter-6-a-lacanian-approach-to-diagnosis", 2),
    ],
    88: [Element("heading", "7. Psychosis", "chapter-7-psychosis", 2)],
    126: [Element("heading", "8. Neurosis", "chapter-8-neurosis", 2)],
    186: [Element("heading", "9. Perversion", "chapter-9-perversion", 2)],
    228: [
        Element("part", "III. Psychoanalytic Technique beyond Desire", "part-iii", 1),
        Element("heading", "10. From Desire to Jouissance", "chapter-10-from-desire-to-jouissance", 2),
    ],
}


SECTION_STARTS_EPUB: dict[str, list[Element]] = {
    "index_split_007.html": [Element("heading", "Preface", "preface", 2)],
    "index_split_012.html": [
        Element("part", "I. Desire and Psychoanalytic Technique", "part-i", 1),
        Element("heading", "1. Desire in Analysis", "chapter-1-desire-in-analysis", 2),
    ],
    "index_split_014.html": [Element("heading", "2. Engaging the Patient in the Therapeutic Process", "chapter-2-engaging-the-patient", 2)],
    "index_split_016.html": [Element("heading", "3. The Analytic Relationship", "chapter-3-the-analytic-relationship", 2)],
    "index_split_018.html": [Element("heading", "4. Interpretation: Opening Up the Space of Desire", "chapter-4-opening-up-the-space-of-desire", 2)],
    "index_split_020.html": [Element("heading", "5. The Dialectic of Desire", "chapter-5-the-dialectic-of-desire", 2)],
    "index_split_024.html": [
        Element("part", "II. Diagnosis and the Positioning of the Analyst", "part-ii", 1),
        Element("heading", "6. A Lacanian Approach to Diagnosis", "chapter-6-a-lacanian-approach-to-diagnosis", 2),
    ],
    "index_split_026.html": [Element("heading", "7. Psychosis", "chapter-7-psychosis", 2)],
    "index_split_028.html": [Element("heading", "8. Neurosis", "chapter-8-neurosis", 2)],
    "index_split_030.html": [Element("heading", "9. Perversion", "chapter-9-perversion", 2)],
    "index_split_034.html": [
        Element("part", "III. Psychoanalytic Technique beyond Desire", "part-iii", 1),
        Element("heading", "10. From Desire to Jouissance", "chapter-10-from-desire-to-jouissance", 2),
    ],
}


VISIBLE_HEADINGS = {
    "Knowledge and Desire",
    "Satisfaction Crisis",
    "The “Preliminary Meetings”: Analytic Pedagogy",
    "The “Preliminary Meetings”: Clinical Aspects",
    "The “Preliminary Meetings”: The Analyst’s Interventions",
    "Punctuation",
    "Scansion",
    "Nothing Can Be Taken at Face Value",
    "Meaning Is Never Obvious",
    "Meaning Is Always Ambiguous",
    "Knowledge and Suggestion",
    "The Subject Supposed to Know",
    "The “Person” of the Analyst",
    "Symbolic Relations",
    "The Analyst as Judge",
    "The Analyst as Cause",
    "Demand versus Desire",
    "Interpretation: Bringing Forth the Lack in Desire",
    "Interpretation as Oracular Speech",
    "Interpretation Hits the Real",
    "Desire Has No Object",
    "Fixation on the Cause",
    "The Other’s Desire as Cause",
    "Separating from the Other’s Desire",
    "The Fundamental Fantasy",
    "The Reconfiguration of the Fundamental Fantasy",
    "Castration and the Fundamental Fantasy",
    "Separation from the Analyst",
    "Foreclosure and the Paternal Function",
    "Consequences of the Failure of the Paternal Function",
    "From Father to Worse",
    "Repression",
    "Lacanian Subject Positions",
    "Hysteria and Obsession",
    "A Case of Obsession",
    "A Case of Hysteria",
    "Etiological Considerations",
    "Phobia",
    "The Core of Human Sexuality",
    "Disavowal",
    "Some Structures of Perversion",
    "Perversion and Jouissance",
    "Castration and the Other",
    "Meta-Considerations",
    "The Paternal Metaphor as Explanatory Principle",
    "Beyond Desire: The Fundamental Fantasy Revisited",
    "From the Subject of Desire to the Subject of Jouissance",
    "Furthering the Analysand’s Eros",
    "Technique beyond Desire",
    "Laying Bare the Subject’s Jouissance",
}


REPLACEMENTS = {
    "intotherapy": "into therapy",
    "deci phering": "deciphering",
    "in-or interested": "in- or interested",
    "who am Ito": "who am I to",
    "may he but": "may be but",
    "ex changed": "exchanged",
    "ethicsabusive": "ethics-abusive",
    "no availthat": "no avail that",
    "analysiswhile": "analysis while",
    "Exaspera tion": "Exasperation",
    "mecha nisms": "mechanisms",
    "flesh-andblood": "flesh-and-blood",
    "fleshandblood": "flesh-and-blood",
    "Name-of-theFather": "Name-of-the-Father",
    "Name-ofthe-Father": "Name-of-the-Father",
    "Name-oftheFather": "Name-of-the-Father",
    "Nameof-theFather": "Name-of-the-Father",
    "Nameof-the-Father": "Name-of-the-Father",
    "Nomdu-Pere": "Nom-du-Père",
    "Nom-du-Pere": "Nom-du-Père",
    "Other’s desirelack": "Other’s desire/lack",
    "laid up": "laid out",
    "lazy so that": "law so that",
    "father-as name": "father-as-name",
    "l.acan": "Lacan",
    "l.acanian": "Lacanian",
    "dtfense": "defense",
    "Jonissance": "Jouissance",
    "jonissance": "jouissance",
    "nlisrecognition": "misrecognition",
    "Desire cones from": "Desire comes from",
    "there isl": "there is",
    "mmniely": "namely",
    "[cravingl": "[craving]",
    "deployedmust": "deployed must",
    "desirenot": "desire - not",
    "wellnot": "well - not",
    "satisfactionwhich": "satisfaction which",
    "hi order to hind anxiety": "in order to bind anxiety",
    "desire-lack": "desire/lack",
    "q ciel ouvert": "à ciel ouvert",
    "a ne rien vouloir savoir": "à ne rien vouloir savoir",
    "fait Ia femme": "fait la femme",
    "Ecole Freudienne": "École Freudienne",
    "Ecole de la Cause Freudienne": "École de la Cause Freudienne",
    "Ecrits": "Écrits",
    "Scilicet (1968):": "Scilicet (1968)",
    "Seminar Vii": "Seminar VII",
    "SE XV1I": "SE XVII",
    "Figure 3..": "Figure 3.",
    "The Analyst as judge": "The Analyst as Judge",
    "standin": "stand-in",
    "remainsat": "remains at",
    "as/of demand": "as/of demand",
    "by he believes": "what he believes",
    "DSM-Ill": "DSM-III",
    "SEXVII": "SE XVII",
    "SaintDenis": "Saint-Denis",
    "reductionism-I": "reductionism - I",
    "there is-Lacan": "there is - Lacan",
    "metaphor-Roger": "metaphor - Roger",
    "found-Lacan’s": "found - Lacan’s",
    "elements-Ratten": "elements - Ratten",
    "terms-Lacan": "terms - Lacan",
    "desire-Lacan’s": "desire - Lacan’s",
    "himselfLacan": "himself - Lacan",
    "jouissanCe": "jouissance",
    "anOther man’s": "another man’s",
    "blow-byblow": "blow-by-blow",
    "returnin other words": "return - in other words",
    "de-Oedipalization-often": "de-Oedipalization - often",
    "work-a certain": "work - a certain",
    "understand-ing": "understanding",
    "misunderstand-ing": "misunderstanding",
    "longstand-ing": "longstanding",
    "notwithstand-ing": "notwithstanding",
    "stand-ing": "standing",
    "under standing": "understanding",
    "SEXVII": "SE XVII",
    "SEX,": "SE X,",
    "mouththe": "mouth - the",
    "analysis-how": "analysis - how",
    "and and every institution": "any and every institution",
    "someThing": "something",
    "Chapter are": "Chapter 8 are",
    "run-of-themill": "run-of-the-mill",
    "tclling": "telling",
    "want-tobe": "want-to-be",
    "preliminaires": "préliminaires",
    "un garcon manque": "un garçon manqué",
    "Jouissance happens.’,’,": "Jouissance happens.",
    "repression.;": "repression.",
    "subjectis": "subject is",
    "reveals to its": "reveals to us",
    "[There isl": "[There is]",
    "Scilicet [19731": "Scilicet [1973]",
    "Reading Seminars I and 11": "Reading Seminars I and II",
    "Chapter in my discussion of the paternal metaphor": "Chapter 7 in my discussion of the paternal metaphor",
    "end of Chapter in the form": "end of Chapter 8 in the form",
}


POST_REPLACEMENTS = {
    "flesh - and-blood": "flesh-and-blood",
    "flesh - andblood": "flesh-and-blood",
    "such - and-such": "such-and-such",
    "desire-desire": "desire - desire",
    "hallucinations-from": "hallucinations - from",
    "stress related”which": "stress related,” which",
    "lives”Now": "lives: “Now",
    "self-consciousness”thought": "self-consciousness,” thought",
    "terminology)”": "terminology),”",
    "herself”What": "herself. “What",
    "women’ reflecting": "women,” reflecting",
    "desire-left": "desire - left",
    "gamblers”)-that": "gamblers”) - that",
    "universe-our": "universe - our",
    "being-bringing": "being - bringing",
    "hand-as": "hand - as",
    "tongue-as": "tongue - as",
    "interpretable-as": "interpretable - as",
    "object-into": "object - into",
    "afterward-as": "afterward - as",
    "argue-as": "argue - as",
    "love-as": "love - as",
    "step-from": "step - from",
    "psychiatry-as": "psychiatry - as",
    "work-in other": "work - in other",
    "therapist-in other": "therapist - in other",
    "imaginary-in other": "imaginary - in other",
    "being-in a word": "being - in a word",
    "life-in cases": "life - in cases",
    "unconscious-in the formations": "unconscious - in the formations",
    "punishment-in a word": "punishment - in a word",
    "fulfill-in short": "fulfill - in short",
    "hate-in a word": "hate - in a word",
    "speculations-in short": "speculations - in short",
    "want-in short": "want - in short",
    "protects-in a word": "protects - in a word",
    "another-in other": "another - in other",
    "psychosis-in other": "psychosis - in other",
    "same-in which": "same - in which",
    "repressed-in one": "repressed - in one",
    "wants-in other": "wants - in other",
    "knowledge-in short": "knowledge - in short",
    "hysteria-in the": "hysteria - in the",
    "desire-in other": "desire - in other",
    "ideals-in other": "ideals - in other",
    "obsession-in the": "obsession - in the",
    "figures-in other": "figures - in other",
    "granted-in other": "granted - in other",
    "father-in order": "father - in order",
    "alienation-in other": "alienation - in other",
    "here-in the sense": "here - in the sense",
    "lineage-in such": "lineage - in such",
    "such-in other": "such - in other",
    "transgression-in other": "transgression - in other",
    "satisfaction-in Jeanne’s": "satisfaction - in Jeanne’s",
    "analyst-to the analyst": "analyst - to the analyst",
    "particular-to say": "particular - to say",
    "sacrifice-to give": "sacrifice - to give",
    "analysis-to guide": "analysis - to guide",
    "unconscious-to make": "unconscious - to make",
    "interpreting-to reestablish": "interpreting - to reestablish",
    "happen-to be": "happen - to be",
    "likely-to elicit": "likely - to elicit",
    "years-to the": "years - to the",
    "process-to elaborate": "process - to elaborate",
    "therapy-to positions": "therapy - to positions",
    "treatises-to divorce": "treatises - to divorce",
    "analysts-to gather": "analysts - to gather",
    "defense-to the": "defense - to the",
    "like-on the": "like - on the",
    "talk-of the": "talk - of the",
    "certainty-of failure": "certainty - of failure",
    "signifier-by the": "signifier - by the",
    "metaphor-by exacting": "metaphor - by exacting",
    "No!-cancels": "No! - cancels",
    "attempts-via": "attempts - via",
    "process-to": "process - to",
    "name-having": "name - having",
    "name-being": "name - being",
    "father-is": "father - is",
    "moments-alienation": "moments - alienation",
    "fantasy-presented": "fantasy - presented",
    "imaginary-in this": "imaginary - in this",
    "being-in other": "being - in other",
    "things-to study": "things - to study",
    "so on-he": "so on - he",
    "psychotic)-but": "psychotic) - but",
    "separation._": "separation.",
    "real-so too": "real - so too",
    "Gelust": "Gelüst",
}


FOREIGN_TERMS = [
    "jouissance",
    "objet a",
    "object a",
    "Nom-du-Père",
    "Name-of-the-Father",
    "Verdrängung",
    "Verleugnung",
    "Verwerfung",
    "Verneinung",
    "à ciel ouvert",
    "à ne rien vouloir savoir",
    "le désir de la mère",
    "fait la femme",
    "vivre la pulsion",
]


def slugify(text: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    base = base or "section"
    slug = base
    count = 2
    while slug in used:
        slug = f"{base}-{count}"
        count += 1
    used.add(slug)
    return slug


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\x0c", "")
    text = text.replace("’", "’").replace("“", "“").replace("”", "”")
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" - ", " - ")
    for src, dst in REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = re.sub(
        r"\b([A-Za-z’]{4,})-(that|which|when|where|what|why|because|otherwise|not|some|they|the|this|these|those|all|often|twice|regardless|and|or|but|must|can|could|would|should|with|without|through|thereby|namely)\b",
        r"\1 - \2",
        text,
    )
    text = re.sub(r"\b(him|her)-or\b", r"\1- or", text)
    text = re.sub(r"\b(him|her)-or herself\b", r"\1- or herself", text)
    for src, dst in POST_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = re.sub(r"([A-Za-z])\s+([,.;:!?])", r"\1\2", text)
    text = re.sub(r"\s+([”’])", r"\1", text)
    text = re.sub(r"([“‘])\s+", r"\1", text)
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    return text.strip()


def join_lines(lines: list[str]) -> str:
    out = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
        elif out.endswith("-"):
            out = out[:-1] + line
        else:
            out += " " + line
    return normalize_text(out)


def extract_lines(page: fitz.Page, page_no: int) -> list[Line]:
    pieces: list[tuple[float, float, float, str]] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            x0, y0, x1, _ = line["bbox"]
            if y0 < 45 or y0 > 725:
                continue
            pieces.append((y0, x0, x1, text))

    groups: list[list[tuple[float, float, float, str]]] = []
    for piece in sorted(pieces, key=lambda item: (item[0], item[1])):
        if groups and abs(groups[-1][0][0] - piece[0]) < 2.2:
            groups[-1].append(piece)
        else:
            groups.append([piece])

    lines: list[Line] = []
    for group in groups:
        group = sorted(group, key=lambda item: item[1])
        text = " ".join(item[3] for item in group)
        x0 = min(item[1] for item in group)
        x1 = max(item[2] for item in group)
        y = min(item[0] for item in group)
        text = normalize_text(text)
        if text:
            lines.append(Line(page_no, y, x0, x1, text))
    return lines


def extract_figures(doc: fitz.Document) -> list[Figure]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figures: list[Figure] = []
    for index, page in enumerate(doc):
        page_no = index + 1
        if page_no == 1:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            filename = "cover.png"
            pix.save(FIGURE_DIR / filename)
            sanitize_png(FIGURE_DIR / filename)
            figures.append(Figure(page_no, 0, f"assets/figures/{filename}", "Cover", "Book cover"))
            continue

        lines = extract_lines(page, page_no)
        captions_by_y = {line.y: line.text for line in lines if re.match(r"^(Figure|Table)\s+\d+", line.text)}
        used_rects: set[tuple[int, int, int, int]] = set()
        for img in page.get_images(full=True):
            xref = img[0]
            for rect in page.get_image_rects(xref):
                area = rect.width * rect.height
                if area < 4500:
                    continue
                key = tuple(round(value) for value in (rect.x0, rect.y0, rect.x1, rect.y1))
                if key in used_rects:
                    continue
                used_rects.add(key)
                margin = 0
                clip = fitz.Rect(
                    max(0, rect.x0 - margin),
                    max(0, rect.y0 - margin),
                    min(page.rect.x1, rect.x1 + margin),
                    min(page.rect.y1, rect.y1 + margin),
                )
                pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=clip, alpha=False)
                filename = f"page-{page_no:03d}-figure-{len(used_rects):02d}.png"
                pix.save(FIGURE_DIR / filename)
                sanitize_png(FIGURE_DIR / filename)
                caption = ""
                below = sorted((abs(y - rect.y1), text) for y, text in captions_by_y.items() if rect.y1 - 10 <= y <= rect.y1 + 55)
                if below:
                    caption = below[0][1]
                if not caption and page_no == 85:
                    caption = "Diagnostic structures and mechanisms"
                alt = caption or f"Figure from PDF page {page_no}"
                figures.append(Figure(page_no, rect.y0, f"assets/figures/{filename}", caption, alt))
    return figures


def sanitize_png(path: Path) -> None:
    # A small number of PyMuPDF crops decode in macOS Preview but report
    # zero natural dimensions in Chromium. Re-encoding with sips fixes that
    # while preserving the visual crop. Other platforms can skip this safely.
    if shutil.which("sips"):
        subprocess.run(["sips", "-s", "format", "png", str(path), "--out", str(path)], check=True, capture_output=True)


def is_caption(line: Line) -> bool:
    return bool(re.match(r"^(Figure|Table)\s+\d+", line.text))


def is_heading(line: Line) -> bool:
    return line.text in VISIBLE_HEADINGS


def is_epigraph_line(line: Line) -> bool:
    return line.x0 > 90 and line.x1 < 540 and (
        line.text.startswith("-")
        or line.text.startswith("[")
        or line.text.startswith("“")
        or "Seminar" in line.text
        or line.text in {
            "Only love allows jouissance to condescend to desire.",
            "Desire is the very essence of man.",
            "What a man actually lacks he aims at.",
            "Subjectification [is] the essential moment of and and every institution of the",
            "The drive couldn’t care less about prohibition; it knows nothing of",
            "What is essential to desire is its impasse. Its crux, says Lacan, is",
        }
    )


def build_elements(doc: fitz.Document, figures: list[Figure]) -> list[Element]:
    elements: list[Element] = [
        Element("title", "A Clinical Introduction to Lacanian Psychoanalysis", "top", 1),
        Element("subtitle", "Theory and Technique"),
        Element("byline", "Bruce Fink"),
        Element(
            "notice",
            "This HTML edition was generated from the local PDF only. The supplied PDF ends mid-chapter on page 241, before the afterword, notes, recommended reading, and index listed for the complete book.",
        ),
    ]
    used_ids = {"top"}
    figures_by_page: dict[int, list[Figure]] = {}
    for figure in figures:
        figures_by_page.setdefault(figure.page, []).append(figure)

    for page_no in range(1, doc.page_count + 1):
        if page_no in SECTION_STARTS:
            for element in SECTION_STARTS[page_no]:
                elements.append(element)
                if element.ident:
                    used_ids.add(element.ident)

        page_figures = sorted(figures_by_page.get(page_no, []), key=lambda fig: fig.y)
        lines = extract_lines(doc[page_no - 1], page_no)

        if page_no == 1:
            if page_figures:
                fig = page_figures[0]
                elements.append(Element("figure", src=fig.src, alt=fig.alt, caption=""))
            continue

        pending: list[str] = []
        fig_index = 0

        def flush_paragraph() -> None:
            nonlocal pending
            if pending:
                text = join_lines(pending)
                if text:
                    elements.append(Element("paragraph", text))
                pending = []

        for line in lines:
            while fig_index < len(page_figures) and page_figures[fig_index].y < line.y - 4:
                flush_paragraph()
                fig = page_figures[fig_index]
                elements.append(Element("figure", src=fig.src, alt=fig.alt, caption=fig.caption))
                fig_index += 1

            if is_caption(line):
                continue

            if is_heading(line):
                flush_paragraph()
                text = normalize_text(line.text)
                ident = slugify(text, used_ids)
                elements.append(Element("heading", text, ident, 3))
                continue

            if is_epigraph_line(line) and line.y < 260:
                flush_paragraph()
                elements.append(Element("quote", normalize_text(line.text)))
                continue

            # A line beginning at the paragraph indent starts a new paragraph
            # unless the previous line clearly continues a sentence.
            if pending and line.x0 > 92:
                previous = pending[-1].strip()
                if re.search(r"[.!?’”)]$", previous):
                    flush_paragraph()
            pending.append(line.text)

        while fig_index < len(page_figures):
            flush_paragraph()
            fig = page_figures[fig_index]
            elements.append(Element("figure", src=fig.src, alt=fig.alt, caption=fig.caption))
            fig_index += 1
        flush_paragraph()

    return elements


def epub_spine(zip_file: zipfile.ZipFile) -> list[str]:
    soup = BeautifulSoup(zip_file.read("content.opf"), "html.parser")
    manifest = {item["id"]: item["href"] for item in soup.find_all("item") if item.get("id") and item.get("href")}
    return [manifest[item["idref"]] for item in soup.find_all("itemref") if item.get("idref") in manifest]


def copy_epub_asset(zip_file: zipfile.ZipFile, src: str) -> str:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"epub-{Path(src).name}"
    target = FIGURE_DIR / filename
    target.write_bytes(zip_file.read(src))
    return f"assets/figures/{filename}"


def caption_text(paragraph) -> str:
    text = normalize_text(paragraph.get_text(" ", strip=True))
    return text if re.match(r"^(Figure|Table)\s+\d+", text) else ""


def build_elements_from_epub() -> list[Element]:
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    elements: list[Element] = [
        Element("title", "A Clinical Introduction to Lacanian Psychoanalysis", "top", 1),
        Element("subtitle", "Theory and Technique"),
        Element("byline", "Bruce Fink"),
        Element(
            "notice",
            "This HTML edition was regenerated from the supplied EPUB text and figures. The EPUB package’s navigation file points an Afterword entry at the final chapter split, but the package itself contains no separate afterword or end-matter document.",
        ),
    ]
    used_ids = {"top"}

    with zipfile.ZipFile(EPUB_PATH) as zip_file:
        if "cover.jpeg" in zip_file.namelist():
            cover_src = copy_epub_asset(zip_file, "cover.jpeg")
            elements.append(Element("figure", src=cover_src, alt="Book cover", caption=""))

        for href in epub_spine(zip_file):
            if href == "titlepage.xhtml":
                continue

            for element in SECTION_STARTS_EPUB.get(href, []):
                elements.append(element)
                if element.ident:
                    used_ids.add(element.ident)

            soup = BeautifulSoup(zip_file.read(href), "html.parser")
            paragraphs = soup.find_all("p")
            skip_indexes: set[int] = set()

            for index, paragraph in enumerate(paragraphs):
                if index in skip_indexes:
                    continue

                image = paragraph.find("img")
                if image and image.get("src"):
                    src = posixpath.normpath(posixpath.join(posixpath.dirname(href), image["src"]))
                    caption = ""
                    for next_index in range(index + 1, min(index + 4, len(paragraphs))):
                        caption = caption_text(paragraphs[next_index])
                        if caption:
                            skip_indexes.add(next_index)
                            break
                        if normalize_text(paragraphs[next_index].get_text(" ", strip=True)):
                            break
                    asset_src = copy_epub_asset(zip_file, src)
                    elements.append(Element("figure", src=asset_src, alt=caption or "Book figure", caption=caption))
                    continue

                text = normalize_text(paragraph.get_text(" ", strip=True))
                if not text or re.match(r"^(Figure|Table)\s+\d+", text):
                    continue

                classes = set(paragraph.get("class") or [])
                if text in VISIBLE_HEADINGS:
                    ident = slugify(text, used_ids)
                    elements.append(Element("heading", text, ident, 3))
                elif "calibre_1" in classes:
                    elements.append(Element("quote", text))
                else:
                    elements.append(Element("paragraph", text))

    return elements


def emphasize_terms(text: str) -> str:
    escaped = html.escape(text, quote=False)
    for term in sorted(FOREIGN_TERMS, key=len, reverse=True):
        escaped_term = html.escape(term, quote=False)
        escaped = re.sub(rf"(?<![\w>])({re.escape(escaped_term)})(?![\w<])", r"<em>\1</em>", escaped)
    return escaped


def nav_headings(elements: list[Element]) -> list[Heading]:
    headings = [Heading(2, "Top", "top")]
    for element in elements:
        if element.kind in {"part", "heading"} and element.ident:
            headings.append(Heading(element.level or 2, element.text, element.ident))
    return headings


def render_html(elements: list[Element]) -> str:
    body = []
    base_headings = nav_headings(elements)
    headings = [base_headings[0], Heading(2, "Contents", "contents"), *base_headings[1:]]
    contents_inserted = False
    for element in elements:
        if element.kind == "title":
            body.append(f'<header class="book-title" id="{element.ident}"><h1>{html.escape(element.text)}</h1>')
        elif element.kind == "subtitle":
            body.append(f'<p class="subtitle">{html.escape(element.text)}</p>')
        elif element.kind == "byline":
            body.append(f'<p class="byline">{html.escape(element.text)}</p></header>')
        elif element.kind == "notice":
            body.append(f'<aside class="source-note">{html.escape(element.text)}</aside>')
            body.append(render_linked_contents(headings))
            contents_inserted = True
        elif element.kind == "part":
            body.append(f'<section class="part" id="{element.ident}"><h2>{html.escape(element.text)}</h2></section>')
        elif element.kind == "heading":
            tag = "h2" if element.level == 2 else "h3"
            ident = f' id="{element.ident}"' if element.ident else ""
            body.append(f"<{tag}{ident}>{html.escape(element.text)}</{tag}>")
        elif element.kind == "paragraph":
            body.append(f"<p>{emphasize_terms(element.text)}</p>")
        elif element.kind == "quote":
            body.append(f"<blockquote>{emphasize_terms(element.text)}</blockquote>")
        elif element.kind == "figure" and element.src:
            caption = f"<figcaption>{html.escape(element.caption)}</figcaption>" if element.caption else ""
            src = image_file_to_data_uri(Path(element.src))
            body.append(f'<figure><img src="{html.escape(src)}" alt="{html.escape(element.alt or "")}">{caption}</figure>')
    if not contents_inserted:
        body.insert(1, render_linked_contents(headings))

    extra_css = """
.book-title{text-align:center;margin-bottom:24px;padding-bottom:28px;border-bottom:1px solid #ded6ca}
.book-title h1{margin-bottom:10px}
.byline{color:#5c5449;margin:0}
.source-note{border-left:4px solid #7a3d00;padding:12px 16px;margin:26px 0 42px;color:#4e4740;background:#f2eee7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.45}
.part{margin:54px 0 32px;padding:28px 0;border-top:1px solid #ded2bd;border-bottom:1px solid #ded2bd}
.part h2{margin:0;text-transform:uppercase}
figure{margin:28px auto 30px;text-align:center}
figure img{max-width:min(100%,560px);height:auto;border:1px solid #e8e0d4;background:white}
figcaption{margin-top:8px;color:#5c5449;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px}
"""
    return wrap_html_document(
        "A Clinical Introduction to Lacanian Psychoanalysis",
        "\n".join(body),
        render_standard_nav(headings),
        css=STANDARD_BOOK_CSS + "\n" + extra_css.strip(),
        script="",
    )


def main() -> None:
    elements = build_elements_from_epub()
    OUTPUT_PATH.write_text(render_html(elements), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Figures: {sum(1 for element in elements if element.kind == 'figure')}")
    print(f"Elements: {len(elements)}")


if __name__ == "__main__":
    main()
