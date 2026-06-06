from __future__ import annotations

import html
import posixpath
import re
import shutil
import sys
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, "../.codex_deps")
sys.path.insert(0, "..")

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning  # type: ignore

from book_conversion_toolkit import (
    Footnote,
    Heading,
    STANDARD_BOOK_CSS,
    clean_spaces,
    image_file_to_data_uri,
    render_footnote_list,
    render_footnote_ref,
    render_linked_contents,
    render_standard_nav,
    slugify,
    wrap_html_document,
)

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


EPUB_PATH = Path("For They Know Not What They Do.epub")
OUTPUT_PATH = Path("for-they-know-not.html")
FIGURE_DIR = Path("assets/figures")

TITLE = "For They Know Not What They Do"
SUBTITLE = "Enjoyment as a Political Factor"
AUTHOR = "Slavoj Žižek"

OMIT_MEMBERS = {
    "OEBPS/Text/coverpage.xhtml",
    "OEBPS/Text/chapter0000.html",
    "OEBPS/Text/chapter0001.html",
    "OEBPS/Text/chapter0003.html",
    "OEBPS/Text/chapter0004.html",
    "OEBPS/Text/chapter0097.html",
}

MEMBER_REPLACEMENTS = {
    "Hegelian Llanguage": "Hegelian Llanguage",
}

TEXT_REPLACEMENTS = {
    "Roudedge": "Routledge",
    "direcdy": "directly",
    "detaded": "detailed",
    "forgetten": "forgotten",
    "mouuement": "mouvement",
    "silendy": "silently",
    "Weatherhilt": "Weatherhill",
    "Causefreudienne": "Cause freudienne",
    "suiprising": "surprising",
    "W estem": "Western",
    "in-between-two-deaths": "in-between-two-deaths",
}

SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


@dataclass(frozen=True)
class NavItem:
    label: str
    member: str
    depth: int


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize_member(src: str) -> str:
    return posixpath.normpath(posixpath.join("OEBPS", src))


def parse_nav() -> list[NavItem]:
    ns = {"n": "http://www.daisy.org/z3986/2005/ncx/"}
    items: list[NavItem] = []
    with zipfile.ZipFile(EPUB_PATH) as archive:
        root = ET.fromstring(archive.read("OEBPS/toc.ncx"))

    def walk(node: ET.Element, depth: int) -> None:
        label = node.find("n:navLabel/n:text", ns)
        content = node.find("n:content", ns)
        if label is not None and content is not None:
            items.append(NavItem(clean_spaces(label.text or ""), normalize_member(content.attrib["src"]), depth))
        for child in node.findall("n:navPoint", ns):
            walk(child, depth + 1)

    nav_map = root.find("n:navMap", ns)
    assert nav_map is not None
    for nav_point in nav_map.findall("n:navPoint", ns):
        walk(nav_point, 0)
    return items


def parse_spine() -> list[str]:
    with zipfile.ZipFile(EPUB_PATH) as archive:
        root = ET.fromstring(archive.read("OEBPS/content.opf"))
    manifest = {
        node.attrib["id"]: normalize_member(node.attrib["href"])
        for node in root.iter()
        if local_name(node.tag) == "item" and "id" in node.attrib and "href" in node.attrib
    }
    return [
        manifest[node.attrib["idref"]]
        for node in root.iter()
        if local_name(node.tag) == "itemref" and node.attrib.get("idref") in manifest
    ]


def apply_text_replacements(text: str) -> str:
    text = clean_spaces(text)
    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def render_image(tag, member: str) -> str:
    with zipfile.ZipFile(EPUB_PATH) as archive:
        src = tag.get("src")
        if not src:
            return ""
        image_member = posixpath.normpath(posixpath.join(posixpath.dirname(member), src))
        filename = posixpath.basename(image_member)
        if filename == "image-0YETYSV2.jpg":
            return ""
        target = FIGURE_DIR / filename
        try:
            data = archive.read(image_member)
        except KeyError:
            return ""
        if not target.exists() or target.read_bytes() != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        src = image_file_to_data_uri(target)
        return (
            f'<figure class="book-figure"><img src="{html.escape(src, quote=True)}" '
            f'alt="Figure from {html.escape(TITLE, quote=True)}" loading="lazy" decoding="async"></figure>'
        )


def note_ident(member: str, label: str) -> str:
    base = Path(member).stem.replace("chapter", "ch")
    return f"{base}-{label}"


def parse_notes() -> dict[tuple[str, str], Footnote]:
    notes: dict[tuple[str, str], Footnote] = {}
    current_label: str | None = None
    current_member: str | None = None
    current_parts: list[str] = []
    with zipfile.ZipFile(EPUB_PATH) as archive:
        soup = BeautifulSoup(archive.read("OEBPS/Text/chapter0097.html").decode("utf-8", errors="replace"), "html.parser")

    def flush() -> None:
        nonlocal current_label, current_member, current_parts
        if current_label is not None and current_member is not None:
            note_html = html.escape(apply_text_replacements(" ".join(current_parts)), quote=False)
            notes[(current_member, current_label)] = Footnote(note_ident(current_member, current_label), current_label, note_html)
        current_label = None
        current_member = None
        current_parts = []

    for tag in soup.find_all(["p", "h3"]):
        if tag.name == "h3":
            flush()
            continue
        text = apply_text_replacements(tag.get_text(" ", strip=True))
        if text == "Notes":
            continue
        match = re.match(r"^(\d{1,3})\.\s+(.*)", text)
        if match:
            flush()
            current_label = match.group(1)
            link = tag.find("a")
            href = link.get("href") if link else ""
            current_member = normalize_member(f"Text/{href.split('#', 1)[0]}") if href else None
            current_parts = [match.group(2)]
        elif current_label is not None and text:
            current_parts.append(text)
    flush()
    return notes


def replace_note_refs(markup: str, member: str, notes: dict[tuple[str, str], Footnote], used_refs: list[Footnote]) -> str:
    def repl(match: re.Match[str]) -> str:
        label = match.group(0).translate(SUPERSCRIPT_DIGITS)
        note = notes.get((member, label))
        if note is None:
            return match.group(0)
        used_refs.append(note)
        return render_footnote_ref(note)

    return re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", repl, markup)


def inline_markup(tag, member: str, notes: dict[tuple[str, str], Footnote], used_refs: list[Footnote]) -> str:
    text = apply_text_replacements(tag.get_text(" ", strip=True))
    return replace_note_refs(html.escape(text, quote=False), member, notes, used_refs)


def heading_level(item: NavItem) -> int:
    if item.label.startswith("Part "):
        return 2
    if re.match(r"^\d+\.\s+", item.label):
        return 2
    if re.match(r"^[IVX]+\.\s+", item.label):
        return 3
    if item.depth <= 0:
        return 2
    return min(4, item.depth + 2)


def render_title_page() -> str:
    return f"""
<section class="title-page" aria-labelledby="title">
  <h1 id="title">For They Know Not<br>What They Do</h1>
  <p class="subtitle">{html.escape(SUBTITLE, quote=False)}</p>
  <p class="author">{html.escape(AUTHOR.upper(), quote=False)}</p>
  <p class="publisher">VERSO<br>London - New York</p>
</section>
<p class="dedication">For Kostja, my son</p>
""".strip()


def compact_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def is_title_fragment(text: str, item: NavItem | None) -> bool:
    if item is None:
        return False
    text_key = compact_title(text)
    label_key = compact_title(item.label)
    return bool(text_key) and text_key in label_key


def build_html() -> str:
    if FIGURE_DIR.exists():
        shutil.rmtree(FIGURE_DIR)
    nav_items = parse_nav()
    nav_by_member = {item.member: item for item in nav_items}
    notes = parse_notes()
    used_ids: dict[str, int] = {"title": 1}
    headings: list[Heading] = []
    used_notes: list[Footnote] = []
    body: list[str] = [render_title_page()]

    with zipfile.ZipFile(EPUB_PATH) as archive:
        for member in parse_spine():
            if member in OMIT_MEMBERS:
                continue
            soup = BeautifulSoup(archive.read(member).decode("utf-8", errors="replace"), "html.parser")
            item = nav_by_member.get(member)

            if member in {"OEBPS/Text/chapter0002.html", "OEBPS/Text/chapter0005.html"}:
                continue

            if item is not None:
                level = heading_level(item)
                ident = slugify(item.label, used_ids)
                headings.append(Heading(level, item.label, ident))
                body.append(f'<h{level} id="{ident}">{html.escape(item.label, quote=False)}</h{level}>')

            skip_heading_texts = {item.label if item else "", "Notes"}
            if item and ":" in item.label:
                skip_heading_texts.update(part.strip() for part in item.label.split(":") if part.strip())
            if item and item.label.startswith("Introduction: "):
                skip_heading_texts.add("INTRODUCTION")
                skip_heading_texts.add(item.label.split(": ", 1)[1])

            seen_content = False
            for tag in soup.find_all(["p", "h2", "h3", "img"]):
                if tag.name == "img":
                    figure = render_image(tag, member)
                    if figure:
                        body.append(figure)
                        seen_content = True
                    continue
                text = apply_text_replacements(tag.get_text(" ", strip=True))
                if not text or text in skip_heading_texts:
                    continue
                if not seen_content and tag.name == "p" and is_title_fragment(text, item):
                    continue
                seen_content = True
                if member == "OEBPS/Text/chapter0005.html" and text == "Contents":
                    continue
                if tag.name in {"h2", "h3"}:
                    sub_level = 3 if tag.name == "h2" else 4
                    ident = slugify(text, used_ids)
                    headings.append(Heading(sub_level, text, ident))
                    body.append(f'<h{sub_level} id="{ident}">{html.escape(text, quote=False)}</h{sub_level}>')
                elif member == "OEBPS/Text/chapter0098.html":
                    css = ' class="index-subentry"' if "style1" in (tag.get("class") or []) else ' class="index-entry"'
                    body.append(f"<p{css}>{inline_markup(tag, member, notes, used_notes)}</p>")
                else:
                    body.append(f"<p>{inline_markup(tag, member, notes, used_notes)}</p>")

    nav_headings = [Heading(2, "Title", "title"), Heading(2, "Contents", "contents"), *headings]
    body.insert(1, render_linked_contents(nav_headings))
    body.append(render_footnote_list(used_notes))
    return wrap_html_document(TITLE, "\n".join(body), render_standard_nav(nav_headings), css=STANDARD_BOOK_CSS)


def main() -> None:
    markup = build_html()
    OUTPUT_PATH.write_text(markup, encoding="utf-8")
    note_refs = markup.count('class="note-ref"')
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Notes: {note_refs}")
    print(f"Figures: {markup.count('<figure')}")


if __name__ == "__main__":
    main()
