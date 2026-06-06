---
name: book-conversion
description: Convert scholarly/theory books from PDF, EPUB, or OCR into reproducible single-file HTML editions with selectable text, navigation, figures, footnotes, validation, and reusable cleanup logic.
---

# Book Conversion

Use this skill when converting books into readable, selectable HTML. The quality bar is script-driven reproducibility: every correction, omission, figure, footnote, and heading decision belongs in code or documented configuration, not in manual edits to generated HTML.

## Start

1. Bootstrap dependencies if the root `.codex_deps/` does not exist:

   ```bash
   bash scripts/bootstrap_deps.sh
   ```

2. In a new book sub-project, insert both paths before imports:

   ```python
   import sys
   sys.path.insert(0, "../.codex_deps")
   sys.path.insert(0, "..")
   ```

3. Use `book_conversion_toolkit` for shared text cleanup, slug generation, PDF line inspection, EPUB spine/member reads, footnote rendering, navigation rendering, and HTML validation.

## Conversion Workflow

1. Map pages first. Use the toolkit CLI to inspect visible page starts:

   ```bash
   python3 -m book_conversion_toolkit inspect-pdf "book.pdf" --pages 1-20 --lines 8
   ```

2. Choose the authority for body text:
   - Use EPUB when it has complete, ordered text and better chapter endings.
   - Use PDF text layer when spans preserve italics, superscript notes, and usable body order.
   - Use OCR when the PDF text layer corrupts many terms or glyphs.
   - Use a hybrid path when EPUB is best for images/index but PDF is best for notes or layout.
3. Build a page/section map and omit non-reading matter explicitly.
4. Centralize cleanup in replacement dictionaries. Include artifact scans for every high-confidence recurring error.
5. Parse structural elements into an intermediate list such as `title`, `part`, `heading`, `paragraph`, `quote`, `figure`, and `index`.
6. Insert footnotes by stable target strings or real PDF superscript metadata. Fail loudly when a target or note is missing.
7. Extract or copy meaningful figures into `assets/figures/`; reject tiny glyph fragments and decorative scans.
8. When an EPUB is available, prefer its structured text, tables, MathML, note links, and image assets over OCR; do not use full-page snapshots for tables or figures unless no structured/cropped source exists.
9. Cross-check EPUB formula, table, and figure blocks against the PDF's layout or PDF-derived image assets. When an EPUB supplies both MathML/text and a rendered image fallback for the same formula or diagram, render only one visible representation; prefer the image fallback when the PDF layout is the authority.
10. Keep the reading surface book-like even when EPUB is the text authority: use the PDF for title/subtitle placement, chapter-opening hierarchy, section heading weight, paragraph indentation, table scale, figure scale, and text-column measure. Do not leave loose EPUB spacing as the default.
11. For PDF block extraction, run paragraph fragments through `merge_continuation_paragraphs` before assigning annotation anchors so page/block breaks like `family` followed by `abandoned...` do not become separate paragraphs.
12. Generate navigation from final headings, not a separate hand-maintained outline. Use both `render_standard_nav` for the fixed side navigator and `render_linked_contents` for the in-body contents section, then wrap with `STANDARD_BOOK_CSS` and `wrap_html_document` so fixed navigation, collapsible draggable nav/text resizing, active-link behavior, in-content links, details expansion, and direct anchor jumps stay consistent across outputs.
13. Use `wrap_html_document` or `add_annotation_anchors` for final HTML so headings and reading blocks have stable annotation anchors.
14. Regenerate and validate after each significant section.

## Toolkit Commands

Validate an output:

```bash
python3 -m book_conversion_toolkit validate-html output.html \
  --expect-note-refs 11 \
  --expect-figures 5 \
  --require-standard-nav \
  --reject-split-paragraphs \
  --scan "known_bad_ocr"
```

Validate all current generated outputs:

```bash
python3 scripts/validate_existing_outputs.py
```

Use JSON output when another script should consume the result:

```bash
python3 -m book_conversion_toolkit validate-html output.html --json
```

## Required Checks

Always check:

- HTML parses enough for anchor scanning.
- Every internal link resolves to an ID.
- IDs are unique.
- Figure files exist and are non-empty.
- Footnote reference, hover popover, and fallback list counts match when that output uses hover notes.
- Known OCR/text-layer artifacts do not remain.
- Excluded metadata/copyright/catalog pages did not leak into the reading text.
- Annotation anchors are present on generated reading blocks. The toolkit adds `data-anchor-id` and, when needed, deterministic `ann-...` IDs scoped to the nearest section.
- The shared standard navigator and in-body linked contents are present and behavior-ready. Run validation with `--require-standard-nav` for all standard generated book outputs; this checks the fixed nav shell, collapsible draggable nav/text separator, linked contents entries, active-link CSS, hashchange handling, details auto-expansion, animation-frame throttling, disabled overscroll, and absence of smooth scrolling.
- For PDF block-based prose outputs, run validation with `--reject-split-paragraphs` after using `merge_continuation_paragraphs`; intentional style changes such as inset quotation blocks should remain distinct.

Use browser/Playwright checks when CSS, navigation, hover notes, mobile behavior, or figures changed.

## Detailed Lessons

Read `references/conversion-guidance.md` when choosing between PDF, EPUB, OCR, or hybrid extraction, or when debugging paragraph merging, note leakage, image extraction, or foreign-language term cleanup.
