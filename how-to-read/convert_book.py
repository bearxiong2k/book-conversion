from __future__ import annotations

import copy
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, "../.codex_deps")
sys.path.insert(0, "..")

from bs4 import BeautifulSoup, NavigableString, Tag  # type: ignore

from book_conversion_toolkit import (
    Footnote,
    Heading,
    STANDARD_BOOK_CSS,
    clean_spaces,
    render_footnote_list,
    render_footnote_ref,
    render_linked_contents,
    render_standard_nav,
    slugify,
    wrap_html_document,
)


EPUB_PATH = Path("How to Read Lacan (How to Read).epub")
OUTPUT_PATH = Path("how-to-read-lacan.html")

TITLE = "How to Read Lacan"
AUTHOR = "Slavoj Žižek"
PUBLISHER = "W. W. Norton & Company"


@dataclass(frozen=True)
class Section:
    member: str
    title: str
    level: int = 2


SECTIONS = [
    Section("index_split_004.html", "Series Editor's Foreword"),
    Section("index_split_005.html", "How am I to read How to Read?", 3),
    Section("index_split_006.html", "Introduction"),
    Section("index_split_008.html", "1. Empty Gestures and Performatives: Lacan Confronts the CIA Plot"),
    Section("index_split_010.html", "2. The Interpassive Subject: Lacan Turns a Prayer Wheel"),
    Section("index_split_012.html", "3. From Che vuoi? to Fantasy: Lacan with Eyes Wide Shut"),
    Section("index_split_014.html", "4. Troubles with the Real: Lacan as a Viewer of Alien"),
    Section("index_split_016.html", "5. Ego Ideal and Superego: Lacan as a Viewer of Casablanca"),
    Section("index_split_018.html", "6. 'God is dead, but He doesn't Know it': Lacan Plays with Bobok"),
    Section("index_split_020.html", "7. The Perverse Subject of Politics: Lacan as a Reader of Mohammad Bouyeri"),
    Section("index_split_022.html", "Chronology"),
    Section("index_split_023.html", "Suggestions for Further Reading"),
    Section("index_split_024.html", "Index"),
    Section("index_split_025.html", "About the Author"),
]

SKIP_DUPLICATE_NOTE_CHAPTER = "index_split_021.html"

TEXT_REPLACEMENTS = {
    "How to Read ?": "How to Read?",
    "amella ": "lamella ",
    "llamella": "lamella",
    "dano ferentes": "dona ferentes",
    "Ecrits": "Ecrits",
    "ecrits": "ecrits",
}


def soup_for(epub: ZipFile, member: str) -> BeautifulSoup:
    return BeautifulSoup(epub.read(member), "html.parser")


def normalized_text(tag: Tag) -> str:
    return clean_spaces(tag.get_text(" ", strip=True)).replace(" ,", ",")


def cleanup_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = clean_spaces(text)
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" ;", ";")
    text = text.replace(" :", ":")
    text = text.replace(" ?", "?")
    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"\bamella\b", "lamella", text)
    return text


def canonical_heading(text: str) -> str:
    text = cleanup_text(text).casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"^\d+\.\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return clean_spaces(text)


def same_heading(source: str, target: str) -> bool:
    source_key = canonical_heading(source)
    target_key = canonical_heading(target)
    return source_key == target_key or source_key in target_key or target_key in source_key


def note_label_from_span(span: Tag) -> str | None:
    label = normalized_text(span)
    if re.fullmatch(r"\d+|\*", label):
        return label
    link = span.find("a")
    if link:
        label = normalized_text(link)
        if re.fullmatch(r"\d+|\*", label):
            return label
    return None


def note_span(tag: Tag) -> Tag | None:
    for span in tag.find_all("span", id=True):
        if span.find("sup") or span.find_parent("sup"):
            continue
        if note_label_from_span(span):
            return span
    return None


def inline_markup(node: Tag | NavigableString, notes: dict[str, Footnote]) -> str:
    if isinstance(node, NavigableString):
        return html.escape(str(node), quote=False)

    if not isinstance(node, Tag):
        return ""

    if node.name == "br":
        return "<br>"

    if node.name == "sup":
        link = node.find("a", href=True)
        if link and link["href"].startswith("#"):
            target = link["href"][1:]
            note = notes.get(target)
            if note:
                return render_footnote_ref(note)

    if node.name == "a":
        href = node.get("href")
        if href and href.startswith("#") and href[1:] in notes:
            return render_footnote_ref(notes[href[1:]])
        if node.get("id") and not href:
            return ""
        inner = "".join(inline_markup(child, notes) for child in node.children)
        if href and re.match(r"^[a-z]+:", href):
            return f'<a href="{html.escape(href, quote=True)}">{inner}</a>'
        return inner

    inner = "".join(inline_markup(child, notes) for child in node.children)
    classes = set(node.get("class") or [])
    if node.name in {"em", "i"} or "italic" in classes:
        return f"<em>{inner}</em>"
    if node.name in {"strong", "b"} or "bold" in classes:
        return f"<strong>{inner}</strong>"
    return inner


def note_body_html(paragraph: Tag, notes: dict[str, Footnote]) -> str:
    clone = copy.copy(paragraph)
    clone.clear()
    for child in paragraph.contents:
        clone.append(copy.copy(child))
    span = note_span(clone)
    if span:
        span.decompose()
    return cleanup_text(inline_markup(clone, notes)).strip()


def extract_notes(soup: BeautifulSoup) -> dict[str, Footnote]:
    notes: dict[str, Footnote] = {}
    used_note_ids: set[str] = set()
    for paragraph in soup.find_all("p"):
        span = note_span(paragraph)
        if not span or not span.get("id"):
            continue
        label = note_label_from_span(span)
        if not label:
            continue
        target = span["id"]
        base = "note-star" if label == "*" else f"note-{label}"
        ident = slugify(base, used_note_ids)
        notes[target] = Footnote(ident, label, note_body_html(paragraph, notes))
    return notes


def is_inside_notes(tag: Tag) -> bool:
    previous = tag
    while previous:
        previous = previous.find_previous(["h1", "h2", "h3", "h4"])
        if previous is None:
            return False
        if normalized_text(previous).lower() == "notes":
            return True
        return False
    return False


def paragraph_html(tag: Tag, notes: dict[str, Footnote], section_title: str = "") -> str:
    text = cleanup_text(inline_markup(tag, notes)).strip()
    if not text:
        return ""
    css = ""
    classes = set(tag.get("class") or [])
    if section_title == "Index":
        css = ' class="index-entry"'
    elif "calibre_21" in classes:
        css = ' class="signature"'
    elif "calibre_19" in classes and not note_span(tag):
        css = ' class="reference-entry"'
    elif "calibre_13" in classes and tag.find_parent("blockquote"):
        css = ' class="epigraph"'
    if tag.find_parent("blockquote") and section_title != "Index":
        return f"<blockquote><p{css}>{text}</p></blockquote>"
    return f"<p{css}>{text}</p>"


def render_title_page() -> str:
    title_id = "title"
    return (
        f'<section id="{title_id}" class="title-page" aria-labelledby="title-heading">\n'
        '<p class="series">How to Read</p>\n'
        f'<h1 id="title-heading">{html.escape(TITLE)}</h1>\n'
        f'<p class="author">{html.escape(AUTHOR)}</p>\n'
        f'<p class="publisher">{html.escape(PUBLISHER)}</p>\n'
        "</section>"
    )


def render_dedication(epub: ZipFile) -> str:
    soup = soup_for(epub, "index_split_002.html")
    text = ""
    for paragraph in soup.find_all("p"):
        candidate = normalized_text(paragraph)
        if candidate and candidate != TITLE:
            text = candidate
            break
    if not text:
        return ""
    return f'<p id="dedication" class="dedication">{html.escape(text, quote=False)}</p>'


def render_section(epub: ZipFile, section: Section, used_ids: set[str], used_notes: list[Footnote]) -> tuple[str, Heading]:
    soup = soup_for(epub, section.member)
    notes = extract_notes(soup)
    ident = slugify(section.title, used_ids)
    heading = Heading(section.level, section.title, ident)
    out = [f'<h{section.level} id="{ident}">{html.escape(section.title, quote=False)}</h{section.level}>']
    seen_notes: set[str] = set()

    for tag in soup.body.find_all(["h1", "h2", "h3", "h4", "p"]):
        text = normalized_text(tag)
        if not text or text == TITLE:
            continue
        if tag.name in {"h1", "h2", "h3", "h4"}:
            if text.lower() == "notes":
                break
            if same_heading(text, section.title):
                continue
            sub_level = min(section.level + 1, 4)
            sub_id = slugify(text, used_ids)
            out.append(f'<h{sub_level} id="{sub_id}">{html.escape(cleanup_text(text), quote=False)}</h{sub_level}>')
            continue
        if is_inside_notes(tag) or note_span(tag):
            continue
        html_text = paragraph_html(tag, notes, section.title)
        if html_text:
            out.append(html_text)
        for link in tag.find_all("a", href=True):
            href = link["href"]
            if href.startswith("#") and href[1:] in notes and href[1:] not in seen_notes:
                used_notes.append(notes[href[1:]])
                seen_notes.add(href[1:])
    return "\n".join(out), heading


def build_html() -> str:
    body: list[str] = [render_title_page()]
    used_ids = {"title", "contents", "dedication", "title-heading"}
    headings = [Heading(2, "Title", "title"), Heading(2, "Contents", "contents")]
    used_notes: list[Footnote] = []

    with ZipFile(EPUB_PATH) as epub:
        dedication = render_dedication(epub)
        if dedication:
            body.append(dedication)
            headings.append(Heading(2, "Dedication", "dedication"))
        section_html: list[str] = []
        section_headings: list[Heading] = []
        for section in SECTIONS:
            rendered, heading = render_section(epub, section, used_ids, used_notes)
            section_html.append(rendered)
            section_headings.append(heading)

    headings.extend(section_headings)
    body.append(render_linked_contents(headings))
    body.extend(section_html)
    body.append(render_footnote_list(used_notes))

    css = (
        STANDARD_BOOK_CSS
        + "\n.title-page{min-height:76vh;display:flex;flex-direction:column;justify-content:center;text-align:center}"
        + "\n.title-page .series{font-variant:small-caps;letter-spacing:.12em;color:#5c5449}"
        + "\n.signature{text-align:right;font-style:italic}"
        + "\n.reference-entry{font-size:.94rem;color:#39342f}"
        + "\n.index-entry{font-size:.94rem;line-height:1.35;margin:0 0 .28rem}"
        + "\n.epigraph{font-size:.96rem;color:#39342f}"
    )
    return wrap_html_document(TITLE, "\n".join(body), render_standard_nav(headings), css=css)


def main() -> None:
    OUTPUT_PATH.write_text(build_html(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
