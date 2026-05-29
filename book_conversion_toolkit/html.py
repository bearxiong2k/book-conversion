from __future__ import annotations

import html
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

    @property
    def ok(self) -> bool:
        return not (
            self.broken_anchors
            or self.duplicate_ids
            or self.missing_images
            or self.empty_images
            or self.artifact_hits
            or self.expectation_failures
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
        ]
        for label, values in (
            ("broken anchors", self.broken_anchors),
            ("duplicate ids", self.duplicate_ids),
            ("missing images", self.missing_images),
            ("empty images", self.empty_images),
            ("artifact hits", self.artifact_hits),
            ("expectation failures", self.expectation_failures),
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


def validate_html(
    path: Path | str,
    artifact_patterns: Iterable[str] = (),
    expected_note_refs: int | None = None,
    expected_figures: int | None = None,
    check_images: bool = True,
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
html { scroll-behavior: smooth; }
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


def wrap_html_document(
    title: str,
    body_html: str,
    nav_html: str = "",
    css: str = DEFAULT_BOOK_CSS,
    script: str = DEFAULT_FOOTNOTE_JS,
    lang: str = "en",
) -> str:
    nav = nav_html or ""
    return (
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
        f"<main>\n{body_html}\n</main>\n"
        "</div>\n"
        f"<script>\n{script}\n</script>\n"
        "</body>\n"
        "</html>\n"
    )
