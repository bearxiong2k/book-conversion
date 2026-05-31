from __future__ import annotations

import argparse
from pathlib import Path

from .html import validate_html
from .sources import extract_pdf_lines, require_fitz


def _parse_pages(value: str) -> list[int]:
    pages: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = (int(item) for item in part.split("-", 1))
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return pages


def cmd_validate_html(args: argparse.Namespace) -> int:
    report = validate_html(
        args.html,
        artifact_patterns=args.scan,
        expected_note_refs=args.expect_note_refs,
        expected_figures=args.expect_figures,
        check_images=not args.no_image_check,
        require_standard_nav=args.require_standard_nav,
    )
    if args.json:
        print(report.to_json())
    else:
        print("\n".join(report.summary_lines()))
    return 0 if report.ok else 1


def cmd_inspect_pdf(args: argparse.Namespace) -> int:
    fitz = require_fitz()
    doc = fitz.open(args.pdf)
    pages = _parse_pages(args.pages) if args.pages else list(range(1, min(doc.page_count, 12) + 1))
    for page_number in pages:
        page = doc[page_number - 1]
        print(f"--- page {page_number} ---")
        lines = extract_pdf_lines(page, page_number, top=args.top, bottom=args.bottom)
        for line in lines[: args.lines]:
            print(f"{line.y:7.1f} {line.x0:7.1f} {line.text}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="book-toolkit", description="Shared utilities for book-to-HTML conversions.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate-html", help="Check anchors, notes, figures, images, and artifact patterns.")
    validate.add_argument("html", type=Path)
    validate.add_argument("--scan", action="append", default=[], help="Regex pattern that must not appear in the HTML.")
    validate.add_argument("--expect-note-refs", type=int)
    validate.add_argument("--expect-figures", type=int)
    validate.add_argument("--no-image-check", action="store_true")
    validate.add_argument(
        "--require-standard-nav",
        action="store_true",
        help="Require the shared fixed navigator, active-link behavior, and no smooth scrolling.",
    )
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate_html)

    inspect = subcommands.add_parser("inspect-pdf", help="Print first positioned text lines for selected PDF pages.")
    inspect.add_argument("pdf", type=Path)
    inspect.add_argument("--pages", help="One-based pages, e.g. 1,3,10-12. Defaults to first 12 pages.")
    inspect.add_argument("--lines", type=int, default=10)
    inspect.add_argument("--top", type=float, default=0)
    inspect.add_argument("--bottom", type=float)
    inspect.set_defaults(func=cmd_inspect_pdf)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
