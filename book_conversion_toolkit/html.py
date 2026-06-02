from __future__ import annotations

import html
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    ident: str


@dataclass(frozen=True)
class Footnote:
    ident: str
    label: str
    html: str


@dataclass
class HtmlValidationReport:
    path: str
    ids: int
    links: int
    broken_anchors: list[str] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    note_refs: int = 0
    floating_notes: int = 0
    fallback_notes: int = 0
    figures: int = 0
    missing_images: list[str] = field(default_factory=list)
    empty_images: list[str] = field(default_factory=list)
    artifact_hits: list[str] = field(default_factory=list)
    expectation_failures: list[str] = field(default_factory=list)
    navigator_failures: list[str] = field(default_factory=list)
    annotation_anchors: int = 0

    @property
    def ok(self) -> bool:
        return not (
            self.broken_anchors
            or self.duplicate_ids
            or self.missing_images
            or self.empty_images
            or self.artifact_hits
            or self.expectation_failures
            or self.navigator_failures
        )

    def to_json(self) -> str:
        payload = asdict(self)
        payload["ok"] = self.ok
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def summary_lines(self) -> list[str]:
        status = "ok" if self.ok else "failed"
        lines = [
            f"validation: {status}",
            f"ids={self.ids} links={self.links} figures={self.figures}",
            f"note_refs={self.note_refs} floating_notes={self.floating_notes} fallback_notes={self.fallback_notes}",
            f"annotation_anchors={self.annotation_anchors}",
        ]
        for label, values in (
            ("broken anchors", self.broken_anchors),
            ("duplicate ids", self.duplicate_ids),
            ("missing images", self.missing_images),
            ("empty images", self.empty_images),
            ("artifact hits", self.artifact_hits),
            ("expectation failures", self.expectation_failures),
            ("navigator failures", self.navigator_failures),
        ):
            if values:
                lines.append(f"{label}: " + ", ".join(values[:20]))
                if len(values) > 20:
                    lines.append(f"{label}: ... {len(values) - 20} more")
        return lines


class _BookHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.note_refs = 0
        self.floating_notes = 0
        self.fallback_notes = 0
        self.figures = 0
        self.images: list[str] = []
        self.annotation_anchors = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        if "id" in data:
            self.ids.append(data["id"])
            if tag == "li" and data["id"].startswith("fn-"):
                self.fallback_notes += 1
        href = data.get("href", "")
        if href.startswith("#"):
            self.hrefs.append(href[1:])
        classes = set(data.get("class", "").split())
        if "note-ref" in classes:
            self.note_refs += 1
        if "floating-note" in classes:
            self.floating_notes += 1
        if tag == "figure":
            self.figures += 1
        if tag == "img" and data.get("src"):
            self.images.append(data["src"])
        if data.get("data-anchor-id"):
            self.annotation_anchors += 1


def validate_html(
    path: Path | str,
    artifact_patterns: Iterable[str] = (),
    expected_note_refs: int | None = None,
    expected_figures: int | None = None,
    check_images: bool = True,
    require_standard_nav: bool = False,
) -> HtmlValidationReport:
    path = Path(path)
    markup = path.read_text(encoding="utf-8")
    parser = _BookHtmlParser()
    parser.feed(markup)

    id_counts: dict[str, int] = {}
    for ident in parser.ids:
        id_counts[ident] = id_counts.get(ident, 0) + 1

    ids = set(parser.ids)
    report = HtmlValidationReport(
        path=str(path),
        ids=len(ids),
        links=len(parser.hrefs),
        broken_anchors=sorted(set(parser.hrefs) - ids),
        duplicate_ids=sorted(ident for ident, count in id_counts.items() if count > 1),
        note_refs=parser.note_refs,
        floating_notes=parser.floating_notes,
        fallback_notes=parser.fallback_notes,
        figures=parser.figures,
        annotation_anchors=parser.annotation_anchors,
    )

    if check_images:
        for src in parser.images:
            if re.match(r"^[a-z]+:", src):
                continue
            image_path = (path.parent / src).resolve()
            if not image_path.exists():
                report.missing_images.append(src)
            elif image_path.stat().st_size == 0:
                report.empty_images.append(src)

    for pattern in artifact_patterns:
        if re.search(pattern, markup, flags=re.IGNORECASE):
            report.artifact_hits.append(pattern)

    if expected_note_refs is not None and parser.note_refs != expected_note_refs:
        report.expectation_failures.append(f"expected {expected_note_refs} note refs, found {parser.note_refs}")
    if expected_figures is not None and parser.figures != expected_figures:
        report.expectation_failures.append(f"expected {expected_figures} figures, found {parser.figures}")
    if parser.note_refs and parser.floating_notes and parser.note_refs != parser.floating_notes:
        report.expectation_failures.append(
            f"note ref/popover mismatch: {parser.note_refs} refs, {parser.floating_notes} popovers"
        )
    if parser.note_refs and parser.fallback_notes and parser.note_refs != parser.fallback_notes:
        report.expectation_failures.append(
            f"note ref/fallback mismatch: {parser.note_refs} refs, {parser.fallback_notes} fallback notes"
        )
    if require_standard_nav:
        required_fragments = {
            "book shell wrapper": '<div class="book-shell">',
            "fixed page navigator": '<nav class="page-nav" aria-label="Section navigation">',
            "navigator list": '<ol class="page-nav-list">',
            "shared active-link styling": ".page-nav a.is-active",
            "navigator link collector": "document.querySelectorAll('.page-nav a[href^=\"#\"]')",
            "navigator parent details expansion": "parent.tagName === 'DETAILS'",
            "navigator hashchange handling": "hashchange",
            "navigator animation-frame throttling": "requestAnimationFrame",
            "disabled overscroll behavior": "overscroll-behavior:none",
            "in-body linked contents section": '<ol class="contents">',
            "draggable nav/text separator": 'class="page-nav-resizer"',
            "resizable nav width variable": "--page-nav-width",
            "resizable main width variable": "--main-text-width",
            "nav resize controller": "bookNavLayout",
            "navigator collapse threshold": "collapseThreshold",
            "hidden navigator class": "is-nav-collapsed",
        }
        for label, fragment in required_fragments.items():
            if fragment not in markup:
                report.navigator_failures.append(f"missing {label}")
        if not re.search(r'<ol class="contents">.*?<a href="#[^"]+"', markup, flags=re.IGNORECASE | re.DOTALL):
            report.navigator_failures.append("missing linked entries in in-body contents")
        if re.search(r"(?<!over)scroll-behavior\s*:", markup, flags=re.IGNORECASE):
            report.navigator_failures.append("smooth scrolling is not allowed for standard navigator outputs")
    return report


def render_footnote_ref(note: Footnote) -> str:
    label = html.escape(note.label, quote=False)
    ident = html.escape(note.ident, quote=True)
    return (
        f'<span class="footnote-popover"><sup id="fnref-{ident}" class="note-ref">'
        f'<a href="#fn-{ident}">{label}</a></sup>'
        f'<span class="floating-note" id="sn-{ident}" role="note">'
        f'<span class="floating-note-number">{label}</span> {note.html}</span></span>'
    )


def render_footnote_list(notes: Iterable[Footnote]) -> str:
    items = []
    seen: set[str] = set()
    for note in notes:
        if note.ident in seen:
            continue
        seen.add(note.ident)
        ident = html.escape(note.ident, quote=True)
        label = html.escape(note.label, quote=False)
        items.append(
            f'<li id="fn-{ident}"><span class="footnote-list-number">{label}.</span> '
            f'{note.html} <a class="backref" href="#fnref-{ident}">back</a></li>'
        )
    if not items:
        return ""
    return '<section class="footnotes" aria-labelledby="footnotes-title">\n<h2 id="footnotes-title">Notes</h2>\n<ol>\n' + "\n".join(items) + "\n</ol>\n</section>"


def render_nav(headings: Iterable[Heading], title: str = "Contents") -> str:
    rows = []
    for heading in headings:
        css = f"nav-level-{heading.level}"
        rows.append(
            f'<li class="{css}"><a href="#{html.escape(heading.ident, quote=True)}">'
            f"{html.escape(heading.text, quote=False)}</a></li>"
        )
    return (
        f'<nav class="book-nav" aria-label="{html.escape(title, quote=True)}">\n'
        f"<ol>\n" + "\n".join(rows) + "\n</ol>\n</nav>"
    )


def render_linked_contents(
    headings: Iterable[Heading],
    title: str = "Contents",
    ident: str = "contents",
    skip_idents: Iterable[str] = ("title", "contents", "dedication", "top", "footnotes", "footnotes-title"),
    max_level: int = 3,
) -> str:
    """Render a generated contents list linked to final section IDs."""

    skip = set(skip_idents)
    rows: list[str] = []
    seen: set[str] = set()
    for heading in headings:
        if heading.ident in skip or heading.ident in seen or heading.level > max_level:
            continue
        seen.add(heading.ident)
        css = f' class="nav-level-{heading.level}"' if heading.level > 1 else ' class="nav-level-1"'
        rows.append(
            f'<li{css}><a href="#{html.escape(heading.ident, quote=True)}">'
            f"{html.escape(heading.text, quote=False)}</a></li>"
        )
    return (
        f'<section aria-labelledby="{html.escape(ident, quote=True)}">\n'
        f'<h2 id="{html.escape(ident, quote=True)}">{html.escape(title, quote=False)}</h2>\n'
        '<ol class="contents">\n'
        + "\n".join(rows)
        + "\n</ol>\n</section>"
    )


def _attr_value(attrs: str, name: str) -> str | None:
    match = re.search(rf'\s{name}="([^"]*)"', attrs)
    return html.unescape(match.group(1)) if match else None


def _set_attr(attrs: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    if re.search(rf'\s{name}="[^"]*"', attrs):
        return re.sub(rf'\s{name}="[^"]*"', f' {name}="{escaped}"', attrs, count=1)
    return attrs.rstrip() + f' {name}="{escaped}"'


def _annotation_text(markup: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", markup, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _annotation_slug(value: str, fallback: str = "section") -> str:
    value = html.unescape(value).lower().replace("'", "").replace("’", "")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or fallback


def add_annotation_anchors(markup: str) -> str:
    """Add deterministic block IDs for external annotation anchoring.

    Headings keep their authored IDs. Paragraph-like reading blocks receive
    content-derived IDs scoped to the nearest section, so regenerated HTML keeps
    anchors stable when unrelated sections change.
    """

    main_match = re.search(r"(<main\b[^>]*>)(?P<body>.*?)(</main>)", markup, flags=re.DOTALL | re.IGNORECASE)
    if not main_match:
        return markup

    existing_ids = set(re.findall(r'\sid="([^"]+)"', markup))
    used_ids = set(existing_ids)

    def unique_ident(base: str) -> str:
        candidate = base
        index = 2
        while candidate in used_ids:
            candidate = f"{base}-{index}"
            index += 1
        used_ids.add(candidate)
        return candidate

    current_section = "front"
    token = re.compile(
        r"<(?P<tag>h[1-6]|p|pre|figure)\b(?P<attrs>[^>]*)>(?P<inner>.*?)</(?P=tag)>",
        flags=re.DOTALL | re.IGNORECASE,
    )

    def replace(match: re.Match[str]) -> str:
        nonlocal current_section
        tag = match.group("tag").lower()
        attrs = match.group("attrs")
        inner = match.group("inner")

        ident = _attr_value(attrs, "id")
        text = _annotation_text(inner)
        if tag.startswith("h"):
            if not ident:
                digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
                ident = unique_ident(f"ann-{tag}-{_annotation_slug(text, tag)}-{digest}")
                attrs = _set_attr(attrs, "id", ident)
            current_section = _annotation_slug(ident, "front")
            anchor = ident
        else:
            if ident:
                anchor = ident
            else:
                digest_source = text or f"{tag}:{match.start()}"
                digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:12]
                base = f"ann-{current_section}-{tag}-{digest}"
                anchor = unique_ident(base)
                attrs = _set_attr(attrs, "id", anchor)

        if not _attr_value(attrs, "data-anchor-id"):
            attrs = _set_attr(attrs, "data-anchor-id", anchor)
        return f"<{tag}{attrs}>{inner}</{tag}>"

    body = token.sub(replace, main_match.group("body"))
    start, end = main_match.span("body")
    return markup[:start] + body + markup[end:]


def render_standard_nav(headings: Iterable[Heading]) -> str:
    """Render the standard fixed, expandable book navigator.

    Structure:
    - top-level h2 items without children render as direct links;
    - h2 items with h3/h4 children render as foldable groups with an overview link;
    - h2 items whose text starts with "Part " group following h2 chapters until the next part.
    """

    items = list(headings)

    def link(item: Heading, class_name: str | None = None) -> str:
        class_attr = f' class="{class_name}"' if class_name else ""
        return f'<a{class_attr} href="#{html.escape(item.ident, quote=True)}">{html.escape(item.text, quote=False)}</a>'

    def has_children(index: int) -> bool:
        if items[index].level != 2:
            return False
        probe = index + 1
        while probe < len(items) and items[probe].level != 2:
            if items[probe].level > 2:
                return True
            probe += 1
        return False

    def render_h2_group(index: int) -> tuple[list[str], int]:
        item = items[index]
        lines = ["<li><details open>", f"<summary>{html.escape(item.text, quote=False)}</summary>", "<ol>"]
        lines.append(f'<li>{link(item, "nav-overview")}</li>')
        index += 1
        while index < len(items) and items[index].level != 2:
            child = items[index]
            lines.append(f'<li class="nav-level-{child.level}">{link(child)}</li>')
            index += 1
        lines.append("</ol></details></li>")
        return lines, index

    lines = [
        '<nav class="page-nav" aria-label="Section navigation">',
        '<p class="page-nav-title">Navigate</p>',
        '<ol class="page-nav-list">',
    ]
    index = 0
    while index < len(items):
        item = items[index]
        if item.level == 2 and item.text.startswith("Part "):
            lines.append("<li><details open>")
            lines.append(f"<summary>{html.escape(item.text, quote=False)}</summary>")
            lines.append("<ol>")
            index += 1
            while index < len(items):
                chapter = items[index]
                if chapter.level == 2 and chapter.text.startswith("Part "):
                    break
                if chapter.level == 2 and has_children(index):
                    group, index = render_h2_group(index)
                    lines.extend(group)
                else:
                    css = f"nav-level-{chapter.level}" if chapter.level > 2 else None
                    lines.append(f"<li>{link(chapter, css)}</li>")
                    index += 1
            lines.append("</ol></details></li>")
            continue
        if item.level == 2 and has_children(index):
            group, index = render_h2_group(index)
            lines.extend(group)
            continue
        css = f"nav-level-{item.level}" if item.level > 2 else None
        lines.append(f"<li>{link(item, css)}</li>")
        index += 1
    lines += ["</ol>", "</nav>"]
    return "\n".join(lines)


STANDARD_BOOK_CSS = """
:root{--page-nav-width:260px;--main-text-width:760px}
html,body{overscroll-behavior:none}
body{font-family:Georgia,'Times New Roman',serif;line-height:1.55;margin:0;background:#f8f6f0;color:#151515}
.book-shell{display:block}
main{max-width:var(--main-text-width);margin:0 auto;padding:48px 24px 80px;background:#fff;min-height:100vh}
.page-nav{position:fixed;top:0;bottom:0;left:0;width:var(--page-nav-width);box-sizing:border-box;padding:28px 18px;background:#f1eadf;border-right:1px solid #ded2bd;overflow:auto}
.page-nav-resizer{position:fixed;z-index:30;top:0;bottom:0;left:var(--page-nav-width);width:10px;margin-left:-5px;cursor:col-resize;user-select:none;touch-action:none}
.page-nav-resizer:after{content:"";position:absolute;top:0;bottom:0;left:4px;border-left:1px solid rgba(122,61,0,.42)}
.page-nav-resizer:hover:after,.page-nav-resizer.is-dragging:after{left:3px;border-left-width:3px;border-left-color:rgba(122,61,0,.76)}
body.is-nav-collapsed .page-nav{visibility:hidden;padding-left:0;padding-right:0;border-right:0;overflow:hidden}
body.is-nav-collapsed .page-nav-resizer{left:0;width:14px;margin-left:0}
body.is-nav-collapsed .page-nav-resizer:after{left:5px;border-left-style:dashed}
body.is-resizing-layout{cursor:col-resize}
.page-nav-title{margin:0 0 18px;font-size:.78rem;line-height:1.2;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#5c5449}
.page-nav ol{list-style:none;margin:0;padding:0}
.page-nav li{margin:0 0 3px}
.page-nav details{margin:0 0 8px}
.page-nav summary{padding:5px 0;color:#2f2a24;font-size:.84rem;line-height:1.22;font-variant:small-caps;letter-spacing:.03em;cursor:pointer}
.page-nav details details summary{font-variant:normal;letter-spacing:0;font-size:.86rem;color:#3f3931}
.page-nav details ol{margin:2px 0 0 10px;padding-left:10px;border-left:1px solid #d8c7a8}
.page-nav a{display:block;padding:4px 0;color:#3f3931;font-size:.84rem;line-height:1.22;text-decoration:none}
.page-nav .nav-overview{color:#6c6256;font-style:italic}
.page-nav .nav-level-3 a,.page-nav a.nav-level-3{padding-left:10px;color:#4b443b}
.page-nav .nav-level-4 a,.page-nav a.nav-level-4{padding-left:20px;color:#5c5449;font-size:.8rem}
.page-nav a:hover,.page-nav a:focus{color:#7a3d00;text-decoration:underline;text-underline-offset:3px}
.page-nav a.is-active{color:#7a3d00;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:4px}
h1,h2{font-weight:600;line-height:1.15;text-align:center}
h1{font-size:2.4rem;margin:80px 0 20px;letter-spacing:.04em;text-transform:uppercase}
h2{font-size:1.65rem;margin:56px 0 28px}
h3{font-size:1.12rem;line-height:1.25;margin:34px 0 14px;text-align:left;font-style:italic}
h4{font-size:1rem;line-height:1.25;margin:24px 0 10px;text-align:left;font-variant:small-caps;letter-spacing:.03em}
.author{text-align:center;font-size:1.25rem;letter-spacing:.08em;margin-top:32px}
.subtitle{text-align:center;font-size:1.08rem;margin:18px 0 0}
.publisher{text-align:center;margin-top:72px;letter-spacing:.05em}
.dedication{text-align:center;margin:52px 0 48px;color:#5c5449}
p{font-size:1.03rem;margin:0 0 1rem}
.contents-entry{margin-top:1.2em;font-weight:700}
.contents-detail{color:#5c5449}
.contents{margin:24px auto 48px;max-width:560px}
.contents li{display:flex;gap:16px;justify-content:space-between;border-bottom:1px dotted #bbb;padding:5px 0}
.contents a{display:block;width:100%;color:#2f2a24;text-decoration:none}
.contents a:hover,.contents a:focus{text-decoration:underline;text-underline-offset:3px}
.contents .nav-level-1{font-variant:small-caps;letter-spacing:.04em}
.contents .nav-level-3{padding-left:18px;font-size:.95rem;color:#5c5449}
.contents span:first-child{padding-right:16px}
.part{font-variant:small-caps;letter-spacing:.04em;margin-top:18px}
.index-entry,.index-subentry{margin-bottom:.22em;line-height:1.35}
.index-subentry{padding-left:1.4em;color:#5c5449}
.bullet{position:relative;padding-left:1.35rem}
.bullet:before{content:'\\2022';position:absolute;left:0;color:#7a3d00}
blockquote{margin:1rem 2rem;font-size:1rem}
.book-figure{margin:1.25rem auto 1.75rem;text-align:center}
.book-figure img{display:block;max-width:100%;height:auto;margin:0 auto}
.book-figure figcaption{font-size:.88rem;color:#5c5449;margin-top:.45rem;font-style:italic}
sup{font-size:.72em;line-height:0}
.footnote-popover{display:inline;position:relative}
.note-ref a{color:#7a3d00;text-decoration:none;border-bottom:1px solid rgba(122,61,0,.35);cursor:help}
.floating-note{position:fixed;left:var(--note-left,0);top:var(--note-top,0);z-index:20;display:none;width:min(340px,calc(100vw - 32px));max-height:min(45vh,360px);overflow:auto;padding:10px 12px 11px;border:1px solid #d8c7a8;border-radius:3px;background:#fffdf8;box-shadow:0 8px 24px rgba(0,0,0,.16);font-size:.82rem;line-height:1.4;color:#4f493f;user-select:text}
.floating-note-number{font-weight:700;color:#7a3d00}
.footnote-popover:hover .floating-note,.footnote-popover:focus-within .floating-note,.footnote-popover.is-open .floating-note{display:block}
.footnotes{border-top:1px solid #ccc;margin-top:42px;padding-top:18px;font-size:.92rem}
.footnotes li{margin:.45rem 0}
.backref{text-decoration:none;margin-left:.35em}
@media (min-width:1220px){body{padding-left:var(--page-nav-width)}.footnotes{display:none}}
@media (min-width:980px) and (max-width:1219px){.page-nav,.page-nav-resizer{display:none}.footnotes{display:none}}
@media (max-width:979px){.page-nav,.page-nav-resizer{display:none}.floating-note{display:none}main{max-width:760px;margin:0 auto;padding:32px 18px 64px}.footnotes{display:block}}
""".strip()


DEFAULT_BOOK_CSS = """
:root {
  color-scheme: light;
  --page: #f8f7f2;
  --ink: #202020;
  --muted: #66635d;
  --line: #d8d2c3;
  --accent: #365f8c;
}
* { box-sizing: border-box; }
html, body {
  overscroll-behavior: none;
}
body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.62;
}
.book-shell {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 260px minmax(0, 760px);
  gap: 52px;
  padding: 40px 28px 80px;
}
.book-nav {
  position: sticky;
  top: 24px;
  align-self: start;
  max-height: calc(100vh - 48px);
  overflow: auto;
  padding-right: 16px;
  border-right: 1px solid var(--line);
  font-family: system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.35;
}
.book-nav ol { list-style: none; margin: 0; padding: 0; }
.book-nav li { margin: 0 0 8px; }
.book-nav a { color: var(--accent); text-decoration: none; }
.nav-level-3 { padding-left: 14px; font-size: 13px; }
.nav-level-4 { padding-left: 28px; font-size: 12px; }
main { min-width: 0; }
h1, h2, h3, h4 { line-height: 1.2; margin: 2.1em 0 0.8em; }
h1 { font-size: 2.4rem; margin-top: 0; }
h2 { font-size: 1.55rem; border-top: 1px solid var(--line); padding-top: 1.4em; }
h3 { font-size: 1.25rem; }
p { margin: 0 0 1.05em; }
blockquote { margin: 1.4em 2em; color: var(--muted); }
.book-figure { margin: 2em 0; text-align: center; }
.book-figure img { max-width: 100%; height: auto; }
.book-figure figcaption { font-family: system-ui, sans-serif; font-size: 0.9rem; color: var(--muted); }
.note-ref a { color: var(--accent); text-decoration: none; }
.footnote-popover { position: relative; white-space: normal; }
.floating-note {
  display: none;
  position: fixed;
  z-index: 20;
  max-width: min(420px, calc(100vw - 40px));
  padding: 12px 14px;
  background: #fffdf8;
  border: 1px solid var(--line);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.16);
  font-size: 0.92rem;
  line-height: 1.45;
}
.footnote-popover:hover .floating-note,
.footnote-popover:focus-within .floating-note,
.floating-note.is-open { display: block; }
.footnotes { border-top: 1px solid var(--line); margin-top: 3em; padding-top: 1em; }
@media (max-width: 860px) {
  .book-shell { display: block; padding: 28px 18px 64px; }
  .book-nav { display: none; }
  .floating-note { display: none !important; }
}
""".strip()


DEFAULT_FOOTNOTE_JS = """
document.querySelectorAll('.footnote-popover').forEach((wrap) => {
  const ref = wrap.querySelector('.note-ref');
  const note = wrap.querySelector('.floating-note');
  if (!ref || !note) return;
  const position = () => {
    const rect = ref.getBoundingClientRect();
    const top = Math.min(window.innerHeight - 24, rect.bottom + 10);
    const left = Math.min(window.innerWidth - note.offsetWidth - 20, Math.max(20, rect.left));
    note.style.top = `${Math.max(20, top)}px`;
    note.style.left = `${left}px`;
  };
  wrap.addEventListener('mouseenter', position);
  wrap.addEventListener('focusin', position);
});
""".strip()


DEFAULT_NAV_JS = """
(() => {
  const links = Array.from(document.querySelectorAll('.page-nav a[href^="#"]'));
  if (!links.length) return;
  const byId = new Map();
  for (const link of links) {
    const id = decodeURIComponent(link.hash.slice(1));
    if (!id) continue;
    if (!byId.has(id)) byId.set(id, []);
    byId.get(id).push(link);
  }
  const targets = Array.from(byId.keys())
    .map((id) => document.getElementById(id))
    .filter(Boolean);
  if (!targets.length) return;
  let activeId = "";
  const setActive = (id) => {
    if (!id || id === activeId) return;
    activeId = id;
    for (const link of links) {
      const active = decodeURIComponent(link.hash.slice(1)) === id;
      link.classList.toggle('is-active', active);
      if (active) {
        let parent = link.parentElement;
        while (parent) {
          if (parent.tagName === 'DETAILS') parent.open = true;
          parent = parent.parentElement;
        }
      }
    }
  };
  const currentTarget = () => {
    const offset = Math.max(96, window.innerHeight * 0.22);
    let current = targets[0];
    for (const target of targets) {
      if (target.getBoundingClientRect().top <= offset) current = target;
      else break;
    }
    return current;
  };
  const update = () => setActive(currentTarget().id);
  let scheduled = false;
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      update();
    });
  };
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', () => {
    const id = decodeURIComponent(location.hash.slice(1));
    if (byId.has(id)) setActive(id);
    else schedule();
  });
  if (location.hash && byId.has(decodeURIComponent(location.hash.slice(1)))) {
    setActive(decodeURIComponent(location.hash.slice(1)));
  } else {
    update();
  }
})();

(() => {
  const nav = document.querySelector('.page-nav');
  const handle = document.querySelector('.page-nav-resizer');
  if (!nav || !handle) return;
  const root = document.documentElement;
  const storageKey = 'bookNavLayout';
  const collapseThreshold = 80;
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const layoutFor = (rawNavWidth) => {
    const viewport = Math.max(320, window.innerWidth || 0);
    const navMax = Math.min(420, Math.max(220, viewport * 0.42));
    const collapsed = rawNavWidth <= collapseThreshold;
    const navWidth = collapsed ? 0 : clamp(rawNavWidth, 180, navMax);
    const mainWidth = clamp(viewport - navWidth - 96, 560, 980);
    document.body.classList.toggle('is-nav-collapsed', collapsed);
    root.style.setProperty('--page-nav-width', `${Math.round(navWidth)}px`);
    root.style.setProperty('--main-text-width', `${Math.round(mainWidth)}px`);
  };
  const readStoredWidth = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
      return Number(saved.navWidth);
    } catch {
      return NaN;
    }
  };
  const currentWidth = () => {
    const stored = readStoredWidth();
    if (Number.isFinite(stored)) return stored;
    return nav.getBoundingClientRect().width || 260;
  };
  const applyStored = () => layoutFor(currentWidth());
  const save = (navWidth) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ navWidth: Math.round(navWidth) }));
    } catch {
      // Ignore storage failures; resizing still works for the current page.
    }
  };
  applyStored();
  window.addEventListener('resize', applyStored);
  handle.addEventListener('pointerdown', (event) => {
    if (event.button !== undefined && event.button !== 0) return;
    event.preventDefault();
    handle.classList.add('is-dragging');
    document.body.classList.add('is-resizing-layout');
    try {
      handle.setPointerCapture?.(event.pointerId);
    } catch {
      // Synthetic checks and some drivers do not expose an active pointer capture target.
    }
    const onMove = (moveEvent) => {
      const width = clamp(moveEvent.clientX, 0, Math.min(420, window.innerWidth * 0.42));
      layoutFor(width);
      save(width);
    };
    const onUp = () => {
      handle.classList.remove('is-dragging');
      document.body.classList.remove('is-resizing-layout');
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      document.removeEventListener('pointercancel', onUp);
    };
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
    document.addEventListener('pointercancel', onUp);
    onMove(event);
  });
})();
""".strip()


def wrap_html_document(
    title: str,
    body_html: str,
    nav_html: str = "",
    css: str = DEFAULT_BOOK_CSS,
    script: str = DEFAULT_FOOTNOTE_JS,
    lang: str = "en",
) -> str:
    nav = nav_html or ""
    resizer = '<div class="page-nav-resizer" role="separator" aria-orientation="vertical" title="Drag to resize navigation and text"></div>\n' if 'class="page-nav"' in nav else ""
    markup = (
        "<!doctype html>\n"
        f'<html lang="{html.escape(lang, quote=True)}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title, quote=False)}</title>\n"
        f"<style>\n{css}\n</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="book-shell">\n'
        f"{nav}\n"
        f"{resizer}"
        f"<main>\n{body_html}\n</main>\n"
        "</div>\n"
        f"<script>\n{script}\n{DEFAULT_NAV_JS}\n</script>\n"
        "</body>\n"
        "</html>\n"
    )
    return add_annotation_anchors(markup)
