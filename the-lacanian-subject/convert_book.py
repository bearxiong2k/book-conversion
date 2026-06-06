from __future__ import annotations

import html
import posixpath
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, "../.codex_deps")
sys.path.insert(0, "..")

from book_conversion_toolkit import (  # noqa: E402
    Heading,
    STANDARD_BOOK_CSS,
    render_linked_contents,
    render_standard_nav,
    slugify,
    wrap_html_document,
)
from book_conversion_toolkit.sources import EPUBPackage  # noqa: E402


EPUB_PATH = Path("The Lacanian Subject.epub")
OUTPUT_PATH = Path("the-lacanian-subject.html")
ASSET_DIR = Path("assets/epub-images")

TITLE = "The Lacanian Subject"
SUBTITLE = "Between Language and Jouissance"
AUTHOR = "Bruce Fink"

INCLUDED_MEMBERS = [
    "OEBPS/xhtml/07_preface.xhtml",
    "OEBPS/xhtml/08_preface1.xhtml",
    "OEBPS/xhtml/09_pt1.xhtml",
    "OEBPS/xhtml/10_ch1.xhtml",
    "OEBPS/xhtml/11_ch2.xhtml",
    "OEBPS/xhtml/12_ch3.xhtml",
    "OEBPS/xhtml/13_pt2.xhtml",
    "OEBPS/xhtml/14_ch4.xhtml",
    "OEBPS/xhtml/15_ch5.xhtml",
    "OEBPS/xhtml/16_ch6.xhtml",
    "OEBPS/xhtml/17_pt3.xhtml",
    "OEBPS/xhtml/18_ch7.xhtml",
    "OEBPS/xhtml/19_ch8.xhtml",
    "OEBPS/xhtml/20_pt4.xhtml",
    "OEBPS/xhtml/21_ch9.xhtml",
    "OEBPS/xhtml/22_ch10.xhtml",
    "OEBPS/xhtml/23_afterword.xhtml",
    "OEBPS/xhtml/24_appendix-a.xhtml",
    "OEBPS/xhtml/25_appendix-b.xhtml",
    "OEBPS/xhtml/26_glossary.xhtml",
    "OEBPS/xhtml/27_acknowledgments.xhtml",
    "OEBPS/xhtml/28_notes.xhtml",
    "OEBPS/xhtml/29_bibliography.xhtml",
    "OEBPS/xhtml/30_index.xhtml",
    "OEBPS/xhtml/31_errata.xhtml",
]

NOTES_MEMBER = "OEBPS/xhtml/28_notes.xhtml"
PASSTHROUGH_TAGS = {
    "a",
    "b",
    "blockquote",
    "caption",
    "div",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "math",
    "menclose",
    "mfrac",
    "mi",
    "mn",
    "mo",
    "mover",
    "mrow",
    "msub",
    "msup",
    "mtable",
    "mtd",
    "mtext",
    "mtr",
    "munder",
    "ol",
    "p",
    "section",
    "small",
    "span",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
    "wbr",
}
VOID_TAGS = {"hr", "img", "wbr"}
INLINE_IMAGE_MEMBERS: set[str] = set()


@dataclass(frozen=True)
class EpubNote:
    ident: str
    label: str
    target_ident: str
    html: str


def render_title_page() -> str:
    return (
        '<section id="title" class="title-page" aria-labelledby="title-heading">\n'
        f'<h1 id="title-heading">{html.escape(TITLE, quote=False)}</h1>\n'
        f'<p class="subtitle">{html.escape(SUBTITLE, quote=False)}</p>\n'
        f'<p class="author">{html.escape(AUTHOR, quote=False)}</p>\n'
        '<p class="dedication">Pour Héloise</p>\n'
        "</section>"
    )


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def attr_value(node: ET.Element, name: str) -> str | None:
    for key, value in node.attrib.items():
        if local_name(key) == name:
            return value
    return None


def role_tokens(node: ET.Element) -> set[str]:
    value = attr_value(node, "role") or ""
    return set(value.split())


def class_tokens(node: ET.Element) -> set[str]:
    value = attr_value(node, "class") or ""
    return set(value.split())


def contains_tag(node: ET.Element, tag_name: str) -> bool:
    return any(local_name(child.tag) == tag_name for child in node.iter())


def is_epub_math_variant(node: ET.Element) -> bool:
    return local_name(node.tag) == "span" and "epub" in class_tokens(node) and contains_tag(node, "math")


def parse_member(package: EPUBPackage, member: str) -> ET.Element:
    return ET.fromstring(package.read_text(member))


def body_element(root: ET.Element) -> ET.Element:
    for node in root.iter():
        if local_name(node.tag) == "body":
            return node
    raise ValueError("EPUB member has no body")


def plain_text(node: ET.Element) -> str:
    pieces: list[str] = []
    if node.text:
        pieces.append(node.text)
    for child in node:
        if "doc-pagebreak" not in role_tokens(child):
            pieces.append(plain_text(child))
        if child.tail:
            pieces.append(child.tail)
    return re.sub(r"\s+", " ", "".join(pieces)).strip()


def heading_text(node: ET.Element) -> str:
    text = plain_text(node)
    return re.sub(r"^(\d+)(?=[A-Za-z])", r"\1 ", text)


def absolute_member(base_member: str, href: str) -> tuple[str, str | None]:
    path, _, fragment = href.partition("#")
    if path:
        member = posixpath.normpath(posixpath.join(posixpath.dirname(base_member), path))
    else:
        member = base_member
    return member, fragment or None


def href_key(base_member: str, href: str) -> tuple[str, str | None]:
    member, fragment = absolute_member(base_member, href)
    return member, fragment


def precompute_ids(package: EPUBPackage, members: list[str]) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    used_ids = {"title", "title-heading", "contents"}
    id_map: dict[tuple[str, str], str] = {}
    member_targets: dict[str, str] = {}
    for member in members:
        body = body_element(parse_member(package, member))
        first_id: str | None = None
        for node in body.iter():
            old_id = attr_value(node, "id")
            if not old_id:
                continue
            new_id = slugify(f"{Path(member).stem}-{old_id}", used_ids)
            id_map[(member, old_id)] = new_id
            if first_id is None:
                first_id = new_id
        member_targets[member] = first_id or slugify(Path(member).stem, used_ids)
    return id_map, member_targets


class EpubRenderer:
    def __init__(self, package: EPUBPackage, id_map: dict[tuple[str, str], str], member_targets: dict[str, str]) -> None:
        self.package = package
        self.id_map = id_map
        self.member_targets = member_targets
        self.headings: list[Heading] = [Heading(2, "Title", "title"), Heading(2, "Contents", "contents")]
        self.notes: dict[tuple[str, str], EpubNote] = {}
        self.used_note_refs: set[str] = set()

    def mapped_id(self, member: str, old_id: str | None) -> str | None:
        if not old_id:
            return None
        return self.id_map.get((member, old_id))

    def rewrite_href(self, member: str, href: str) -> str:
        if re.match(r"^[a-z][a-z0-9+.-]*:", href, flags=re.IGNORECASE):
            return href
        target_member, fragment = href_key(member, href)
        if fragment:
            mapped = self.id_map.get((target_member, fragment))
            if mapped:
                return f"#{mapped}"
        if target_member in self.member_targets:
            return f"#{self.member_targets[target_member]}"
        return "#"

    def rewrite_image(self, member: str, src: str) -> str:
        source_member, _ = absolute_member(member, src)
        target = ASSET_DIR / Path(source_member).name
        self.package.extract_member(source_member, target)
        return f"assets/epub-images/{html.escape(target.name, quote=True)}"

    def render_attrs(self, node: ET.Element, member: str) -> str:
        attrs: list[str] = []
        for raw_key, raw_value in node.attrib.items():
            key = local_name(raw_key)
            if key == "id":
                value = self.mapped_id(member, raw_value)
                if value:
                    attrs.append(f'id="{html.escape(value, quote=True)}"')
            elif key == "href":
                attrs.append(f'href="{html.escape(self.rewrite_href(member, raw_value), quote=True)}"')
            elif key == "src":
                attrs.append(f'src="{self.rewrite_image(member, raw_value)}"')
            elif key == "aria-labelledby":
                parts = [self.mapped_id(member, part) or part for part in raw_value.split()]
                attrs.append(f'aria-labelledby="{html.escape(" ".join(parts), quote=True)}"')
            elif key in {
                "alt",
                "aria-label",
                "class",
                "colspan",
                "display",
                "notation",
                "role",
                "rowspan",
                "scope",
            }:
                attrs.append(f'{key}="{html.escape(raw_value, quote=True)}"')
        return (" " + " ".join(attrs)) if attrs else ""

    def render_note_ref(self, note: EpubNote, ref_ident: str) -> str:
        safe_ref = html.escape(ref_ident, quote=True)
        safe_target = html.escape(note.target_ident, quote=True)
        label = html.escape(note.label, quote=False)
        return (
            f'<span class="footnote-popover"><sup id="{safe_ref}" class="note-ref">'
            f'<a href="#{safe_target}">{label}</a></sup>'
            f'<span class="floating-note" id="sn-{safe_ref}" role="note">'
            f'<span class="floating-note-number">{label}</span> {note.html}</span></span>'
        )

    def find_noteref_anchor(self, node: ET.Element) -> ET.Element | None:
        for child in node.iter():
            if local_name(child.tag) == "a" and "doc-noteref" in role_tokens(child):
                return child
        return None

    def render_children(self, node: ET.Element, member: str, collect_headings: bool = True) -> str:
        pieces: list[str] = []
        if node.text:
            pieces.append(html.escape(node.text, quote=False))
        for child in node:
            pieces.append(self.render_node(child, member, collect_headings))
            if child.tail:
                pieces.append(html.escape(child.tail, quote=False))
        return "".join(pieces)

    def render_node(self, node: ET.Element, member: str, collect_headings: bool = True) -> str:
        tag = local_name(node.tag)
        if is_epub_math_variant(node):
            return ""
        if "doc-pagebreak" in role_tokens(node):
            ident = self.mapped_id(member, attr_value(node, "id"))
            aria = attr_value(node, "aria-label")
            attrs = ['class="pagebreak"']
            if ident:
                attrs.append(f'id="{html.escape(ident, quote=True)}"')
            if aria:
                attrs.append(f'aria-label="{html.escape(aria, quote=True)}"')
            return f'<span {" ".join(attrs)}></span>'
        if tag in {"body", "hgroup", "header"}:
            return self.render_children(node, member, collect_headings)
        if tag == "sup":
            anchor = self.find_noteref_anchor(node)
            if anchor is not None:
                href = attr_value(anchor, "href") or ""
                target_member, fragment = href_key(member, href)
                note = self.notes.get((target_member, fragment or ""))
                ref_ident = self.mapped_id(member, attr_value(anchor, "id")) or note.ident if note else None
                if note and ref_ident:
                    self.used_note_refs.add(ref_ident)
                    return self.render_note_ref(note, ref_ident)
        if tag not in PASSTHROUGH_TAGS:
            return self.render_children(node, member, collect_headings)

        attrs = self.render_attrs(node, member)
        if tag == "img":
            image_member, _ = absolute_member(member, attr_value(node, "src") or "")
            if "inline" in class_tokens(node):
                INLINE_IMAGE_MEMBERS.add(image_member)
        if tag.startswith("h") and tag[1:].isdigit() and collect_headings:
            ident = self.mapped_id(member, attr_value(node, "id"))
            if ident:
                original_level = int(tag[1:])
                level = 2 if original_level <= 2 else min(original_level, 4)
                self.headings.append(Heading(level, heading_text(node), ident))
        if tag in VOID_TAGS:
            return f"<{tag}{attrs}>"
        return f"<{tag}{attrs}>{self.render_children(node, member, collect_headings)}</{tag}>"

    def render_note_body(self, li_node: ET.Element, member: str) -> str:
        pieces: list[str] = []
        first_note_para = True
        for child in li_node:
            if local_name(child.tag) == "p" and first_note_para:
                first_note_para = False
                if child.text:
                    pieces.append(html.escape(child.text, quote=False))
                for grandchild in child:
                    if "doc-pagebreak" in role_tokens(grandchild):
                        if grandchild.tail:
                            pieces.append(html.escape(grandchild.tail, quote=False))
                        continue
                    if "doc-backlink" in role_tokens(grandchild) or any("doc-backlink" in role_tokens(n) for n in grandchild.iter()):
                        if grandchild.tail:
                            pieces.append(html.escape(re.sub(r"^\.\s*", "", grandchild.tail), quote=False))
                        continue
                    pieces.append(self.render_node(grandchild, member, collect_headings=False))
                    if grandchild.tail:
                        pieces.append(html.escape(grandchild.tail, quote=False))
            else:
                if "doc-pagebreak" in role_tokens(child):
                    if child.tail:
                        pieces.append(html.escape(child.tail, quote=False))
                    continue
                pieces.append(self.render_node(child, member, collect_headings=False))
                if child.tail:
                    pieces.append(html.escape(child.tail, quote=False))
        return re.sub(r"\s+", " ", "".join(pieces)).strip()

    def load_notes(self) -> None:
        body = body_element(parse_member(self.package, NOTES_MEMBER))
        for li in body.iter():
            if local_name(li.tag) != "li":
                continue
            backlink = None
            for node in li.iter():
                if local_name(node.tag) == "a" and "doc-backlink" in role_tokens(node):
                    backlink = node
                    break
            if backlink is None:
                continue
            note_id = attr_value(backlink, "id")
            if not note_id:
                continue
            target_ident = self.mapped_id(NOTES_MEMBER, note_id)
            if not target_ident:
                continue
            label = plain_text(backlink)
            note = EpubNote(
                ident=target_ident,
                label=label,
                target_ident=target_ident,
                html=self.render_note_body(li, NOTES_MEMBER),
            )
            self.notes[(NOTES_MEMBER, note_id)] = note

    def render_member(self, member: str) -> str:
        body = body_element(parse_member(self.package, member))
        return self.render_node(body, member)


def build_html() -> str:
    package = EPUBPackage(EPUB_PATH)
    if ASSET_DIR.exists():
        shutil.rmtree(ASSET_DIR)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    id_map, member_targets = precompute_ids(package, INCLUDED_MEMBERS)
    renderer = EpubRenderer(package, id_map, member_targets)
    renderer.load_notes()

    body_fragments = [renderer.render_member(member) for member in INCLUDED_MEMBERS]
    fragments = [render_title_page(), render_linked_contents(renderer.headings, max_level=3), *body_fragments]

    css = (
        STANDARD_BOOK_CSS
        + "\n.title-page{min-height:72vh;display:flex;flex-direction:column;justify-content:center;text-align:center}"
        + "\n.title-page .subtitle{font-size:1.15rem;color:#5c5449}"
        + "\n.title-page .author{font-size:1.2rem;letter-spacing:.08em}"
        + "\nhgroup{display:block}"
        + "\nsection{margin:0 0 1rem}"
        + "\n.CN,.PN,.APN{display:block;font-size:.9em;color:#5c5449}"
        + "\n.CT,.PT,.APH{display:block}"
        + "\n.PART{margin-top:72px}"
        + "\n.CAP,.TT,.TT1{text-align:center;font-style:italic;color:#5c5449;margin:.25rem 0 .5rem}"
        + "\n.BL{position:relative;padding-left:1.35rem}"
        + "\n.BL::before{content:''}"
        + "\nfigure.img,figure.img-1,figure.img-nt,.book-figure{margin:1.35rem auto 1.8rem;text-align:center}"
        + "\nfigure img{display:block;max-width:100%;height:auto;margin:0 auto}"
        + "\nimg.inline{display:inline-block;width:auto;max-height:1.1em;vertical-align:-.12em;margin:0 .08em}"
        + "\nimg[role='presentation']:not(.inline){display:block;max-width:100%;height:auto;margin:1rem auto}"
        + "\ntable{width:auto;max-width:100%;border-collapse:collapse;margin:1.25rem auto 1.75rem;font-size:.92rem;line-height:1.32}"
        + "\nth,td{border:1px solid #d8d0c5;padding:.28rem .45rem;vertical-align:middle;text-align:center}"
        + "\ntd p,th p{margin:.08rem 0;font-size:inherit;line-height:inherit}"
        + "\n.TB-nbor,.TB-nbor-th{border:0}"
        + "\nblockquote{border-left:2px solid #d8c7a8;margin:1.2rem 1.5rem;padding-left:1rem;color:#3f3931}"
        + "\n.transition_sb{border:0;border-top:1px solid #d8c7a8;margin:1.5rem auto;width:40%}"
        + "\n.strikethrough{text-decoration:line-through}"
        + "\nsmall{font-size:.78em}"
        + "\nmath{font-family:Georgia,'Times New Roman',serif}"
        + "\n.IX,.IXA{font-size:.9rem;line-height:1.35;margin-bottom:.18rem}"
        + "\n.BIB{font-size:.94rem;line-height:1.42;text-align:left}"
        + "\n.NTX,.noteish{font-size:.92rem;color:#39342f}"
        + "\n@media (max-width:760px){table{display:block;overflow-x:auto}th,td{min-width:3rem}}"
    )
    return wrap_html_document(TITLE, "\n".join(fragments), render_standard_nav(renderer.headings), css=css)


def main() -> None:
    markup = build_html()
    OUTPUT_PATH.write_text(markup, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Figures: {markup.count('<figure')}")
    print(f"Note refs: {markup.count('class=\"note-ref\"')}")


if __name__ == "__main__":
    main()
