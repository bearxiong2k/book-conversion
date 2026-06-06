from __future__ import annotations

import html
import base64
import mimetypes
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
    require_fitz,
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
TRIMMED_IMAGE_PATHS: set[Path] = set()
TOSS_GRID_ROWS = {
    "1 2 3 4 5 6 7 8 9 Toss Numbers": (("1", "2", "3", "4", "5", "6", "7", "8", "9"), "Toss Numbers"),
    "+ + – – + – – – + Heads/Tails Chain": (("+", "+", "–", "–", "+", "–", "–", "–", "+"), "Heads/Tails Chain"),
}


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


def trim_image_whitespace(path: Path, padding: int = 18, threshold: int = 248) -> None:
    if path in TRIMMED_IMAGE_PATHS:
        return
    TRIMMED_IMAGE_PATHS.add(path)
    fitz = require_fitz()
    pix = fitz.Pixmap(path)
    if pix.width <= 0 or pix.height <= 0 or pix.n < 3:
        return
    samples = pix.samples
    stride = pix.n
    min_x, min_y = pix.width, pix.height
    max_x, max_y = -1, -1
    for y in range(pix.height):
        row = y * pix.width * stride
        for x in range(pix.width):
            i = row + x * stride
            channels = samples[i : i + 3]
            alpha = samples[i + 3] if pix.alpha and stride > 3 else 255
            if alpha > 8 and any(channel < threshold for channel in channels):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < 0:
        return
    min_x = max(0, min_x - padding)
    min_y = max(0, min_y - padding)
    max_x = min(pix.width - 1, max_x + padding)
    max_y = min(pix.height - 1, max_y + padding)
    if min_x == 0 and min_y == 0 and max_x == pix.width - 1 and max_y == pix.height - 1:
        return
    source_rect = fitz.IRect(min_x, min_y, max_x + 1, max_y + 1)
    cropped = fitz.Pixmap(pix.colorspace, fitz.IRect(0, 0, source_rect.width, source_rect.height), pix.alpha)
    cropped.clear_with(255)
    cropped.set_origin(source_rect.x0, source_rect.y0)
    cropped.copy(pix, source_rect)
    cropped.set_origin(0, 0)
    cropped.save(path)


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
        trim_image_whitespace(target)
        mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = base64.b64encode(target.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{data}"

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

    def render_toss_grid_row(self, node: ET.Element, member: str) -> str | None:
        row = TOSS_GRID_ROWS.get(plain_text(node))
        if not row:
            return None
        cells, label = row
        attrs = self.render_attrs(node, member)
        if 'class="' in attrs:
            attrs = attrs.replace('class="', 'class="toss-grid-row ', 1)
        else:
            attrs += ' class="toss-grid-row"'
        cell_markup = "".join(f"<span>{html.escape(cell, quote=False)}</span>" for cell in cells)
        return (
            f"<p{attrs}>"
            f'<span class="toss-grid">{cell_markup}</span>'
            f'<span class="toss-grid-label">{html.escape(label, quote=False)}</span>'
            "</p>"
        )

    def render_node(self, node: ET.Element, member: str, collect_headings: bool = True) -> str:
        tag = local_name(node.tag)
        if is_epub_math_variant(node):
            return ""
        if tag == "hr" and "transition_sb" in class_tokens(node):
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

        if tag == "p" and "EQ" in class_tokens(node):
            toss_grid_row = self.render_toss_grid_row(node, member)
            if toss_grid_row:
                return toss_grid_row

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
        + "\n:root{--main-text-width:760px}"
        + "\nmain{padding:64px 52px 88px}"
        + "\nmain p{font-size:1rem;line-height:1.34;margin:0;text-align:justify}"
        + "\n.title-page{min-height:78vh;display:block;text-align:center;padding-top:18vh}"
        + "\n.title-page h1{font-size:2.25rem;line-height:1.02;letter-spacing:.08em;margin:0 0 2.6rem;text-transform:uppercase}"
        + "\n.title-page .subtitle{font-size:1.35rem;line-height:1.32;color:#28231f;max-width:17rem;margin:0 auto 7.5rem}"
        + "\n.title-page .author{font-size:1.25rem;letter-spacing:.22em;text-transform:uppercase;margin-top:0}"
        + "\nhgroup{display:block}"
        + "\nsection{margin:0}"
        + "\nh1.FMH{font-size:1.45rem;line-height:1.2;margin:4.5rem 0 2.1rem;text-align:center;letter-spacing:0;text-transform:none}"
        + "\nh2.CHAPTER{font-size:1rem;line-height:1.2;text-align:left;margin:4.4rem 0 3.1rem;font-weight:700;letter-spacing:0}"
        + "\nh2.CHAPTER .CN{display:flex;align-items:center;gap:.75rem;font-size:1.9rem;line-height:1;margin:0 0 1.35rem;color:#111}"
        + "\nh2.CHAPTER .CN::after{content:'';height:1px;background:#4a453e;flex:1}"
        + "\nh2.CHAPTER .CT{display:block;font-size:1.26rem;line-height:1.18;font-weight:700;color:#111}"
        + "\nh2.CHAPTER [role='doc-subtitle']{display:block;margin-top:.18rem;font-size:.96em}"
        + "\n.PART{margin:6rem 0 5rem;text-align:center}"
        + "\n.PART .PN{display:block;font-size:.9rem;letter-spacing:.18em;text-transform:uppercase;color:#4f493f;margin-bottom:1rem}"
        + "\n.PART .PT{display:block;font-size:1.22rem;line-height:1.2;font-weight:700;letter-spacing:.08em;text-transform:uppercase}"
        + "\n.CN,.PN,.APN{display:block;color:#5c5449}"
        + "\n.CT,.PT,.APH{display:block}"
        + "\nh2.H1,h3.H1,h3.H2,h4.H2{font-size:1.08rem;line-height:1.2;margin:2.65rem 0 1.15rem;text-align:left;font-style:normal;font-weight:700;letter-spacing:0}"
        + "\nh3.H2,h4.H2{font-size:.96rem;text-transform:uppercase;letter-spacing:.06em;margin-top:2rem}"
        + "\np.TX,p.TXS,p.SB1,p.NTX{text-indent:1.28em}"
        + "\np.TNI,p.TNIS,p.STNI,p.CO,p.CAP,p.TT,p.TT1,p.math,td p,th p{text-indent:0}"
        + "\nh1.FMH + p,h2.CHAPTER + p,h2.H1 + p,h3.H1 + p,h3.H2 + p,h4.H2 + p{text-indent:0}"
        + "\np.CO{margin-bottom:0}"
        + "\np.SB1{margin-top:.75rem}"
        + "\np.TXS,p.STNI,p.TNIS{font-size:.95rem;line-height:1.32}"
        + "\np.EQ{font-size:1.05rem;line-height:1.32;text-align:center;text-indent:0;white-space:pre-wrap;margin:.55rem auto;font-variant-numeric:tabular-nums}"
        + "\np.EQ.toss-grid-row{display:flex;align-items:baseline;justify-content:center;gap:1.1rem;white-space:normal;overflow-x:auto;text-align:left}"
        + "\n.toss-grid{display:grid;grid-template-columns:repeat(9,2ch);column-gap:.55ch;font-family:'Courier New',Courier,monospace;font-variant-numeric:tabular-nums;text-align:center;flex:0 0 auto}"
        + "\n.toss-grid span{display:block;text-align:center}"
        + "\n.toss-grid-label{white-space:nowrap;flex:0 0 auto}"
        + "\n.CAP,.TT,.TT1{text-align:left;font-style:normal;color:#111;margin:.2rem 0 .35rem;font-size:.86rem;line-height:1.2;font-weight:700}"
        + "\n.BL{position:relative;padding-left:1.2rem}"
        + "\n.BL::before{content:''}"
        + "\nfigure.img,figure.img-1,figure.img-nt,.book-figure{margin:.75rem auto 1.2rem;text-align:center}"
        + "\nfigure img{display:block;max-width:min(100%,28rem);max-height:22rem;width:auto;height:auto;margin:0 auto}"
        + "\nfigure.img-1 img{max-width:min(100%,23rem);max-height:15rem}"
        + "\nfigure img.img1{max-width:min(100%,8.5rem);max-height:8.5rem}"
        + "\nfigure img.img50{max-width:min(100%,15rem);max-height:14rem}"
        + "\nfigure img.img60{max-width:min(100%,18rem);max-height:16rem}"
        + "\nfigure img.img70{max-width:min(100%,21rem);max-height:18rem}"
        + "\nfigure img.img80{max-width:min(100%,23rem);max-height:19rem}"
        + "\nfigure img.img90{max-width:min(100%,25rem);max-height:20rem}"
        + "\nfigure img.img100{max-width:min(100%,26rem);max-height:21rem}"
        + "\nfigure.img-nt img{max-width:min(100%,32rem);max-height:24rem}"
        + "\np.math{margin:.6rem auto .95rem;text-align:center}"
        + "\np.math img[role='presentation']{max-width:min(100%,22rem);max-height:4.4rem;width:auto;height:auto;margin:.1rem auto .25rem}"
        + "\nimg.inline{display:inline-block;width:auto;max-height:1.1em;vertical-align:-.12em;margin:0 .08em}"
        + "\nimg[role='presentation']:not(.inline){display:block;max-width:min(100%,22rem);height:auto;margin:.75rem auto 1rem}"
        + "\ntable{width:auto;max-width:100%;border-collapse:collapse;margin:.4rem auto 1.1rem;font-size:.92rem;line-height:1.25}"
        + "\nth,td{border:1px solid #2b2926;padding:.4rem .6rem;vertical-align:middle;text-align:left}"
        + "\ntd p,th p{margin:.08rem 0;font-size:inherit;line-height:inherit}"
        + "\n.TB-nbor,.TB-nbor-th{border:0}"
        + "\nblockquote{border-left:0;margin:.9rem 2.1rem;color:#111}"
        + "\nblockquote[role='doc-epigraph']{max-width:34rem;margin:1.3rem auto 1.75rem;padding:0;text-align:left}"
        + "\nblockquote[role='doc-epigraph'] p{font-size:1.08rem;line-height:1.32;text-align:left;text-indent:0;margin:0}"
        + "\nblockquote[role='doc-epigraph'] p.EPC,blockquote[role='doc-epigraph'] p.PEPC{margin:.15rem 0 1rem 2.1rem;font-size:1rem;line-height:1.25}"
        + "\np.EXO,p.VL{font-size:.95rem;line-height:1.32;text-align:justify;text-indent:0}"
        + "\n.strikethrough{text-decoration:line-through}"
        + "\nsmall{font-size:.78em}"
        + "\nmath{font-family:Georgia,'Times New Roman',serif}"
        + "\n.IX,.IXA{font-size:.9rem;line-height:1.35;margin-bottom:.18rem}"
        + "\n.BIB{font-size:.94rem;line-height:1.32;text-align:left;text-indent:0;margin-bottom:.35rem}"
        + "\n.NTX,.noteish{font-size:.92rem;color:#39342f}"
        + "\n@media (max-width:760px){main{padding:36px 20px 64px}main p{text-align:left}.title-page{padding-top:12vh}.title-page .subtitle{margin-bottom:4rem}table{display:block;overflow-x:auto}th,td{min-width:3rem}p.TX,p.TXS,p.SB1,p.NTX{text-indent:1em}p.EQ.toss-grid-row{justify-content:flex-start}.toss-grid{grid-template-columns:repeat(9,1.8ch);column-gap:.35ch}}"
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
