---
name: book-conversion
description: Convert scholarly/theory books from PDF, EPUB, or OCR into reproducible single-file HTML editions with selectable text, navigation, figures, footnotes, validation, and reusable cleanup logic.
---

# Book Conversion

Use this skill when converting books into readable, selectable HTML. The quality
bar is script-driven reproducibility: every correction, omission, figure,
footnote, and heading decision belongs in converter code or book-specific
configuration, never in manual edits to generated HTML.

Keep the repo practical. Add shared structure only when it removes real
duplication, makes checks enforceable, or keeps book-specific decisions easier to
find.

## Start

Bootstrap root dependencies if needed:

```bash
bash scripts/bootstrap_deps.sh
```

In a book sub-project, import root dependencies and toolkit helpers:

```python
import sys
sys.path.insert(0, "../.codex_deps")
sys.path.insert(0, "..")
```

## Workflow

1. Map the source before full extraction:

   ```bash
   python3 -m book_conversion_toolkit inspect-pdf "book.pdf" --pages 1-20 --lines 8
   ```

2. Choose the text authority: EPUB, PDF text layer, OCR, or a hybrid. See
   `references/source-selection.md`.
3. Keep book-specific page maps, omitted pages, figure maps, footnote targets,
   replacement dictionaries, and artifact scans beside the converter.
4. Move only stable mechanics into `book_conversion_toolkit/`.
5. Generate standard outputs with `render_standard_nav`,
   `render_linked_contents`, `STANDARD_BOOK_CSS`, and `wrap_html_document`.
6. Preserve adjustable reading width. Constrain only specific figures, labels,
   tables, formulas, or captions that would otherwise break.
7. Regenerate and validate after meaningful changes.

## Validation

Validate one output:

```bash
python3 -m book_conversion_toolkit validate-html output.html \
  --expect-note-refs 11 \
  --expect-figures 5 \
  --require-self-contained-images \
  --require-standard-nav \
  --reject-split-paragraphs \
  --scan "known_bad_ocr"
```

Validate all current outputs:

```bash
python3 scripts/quality_gate.py
```

Use browser checks when CSS, navigation, hover notes, mobile behavior, formulas,
or figures changed. For standard navigation, verify the side navigator can
collapse and reopen by dragging the separator after increasing text size,
changing reading width, or using Chrome zoom such as 125% and 150%.

## Required Output Properties

- Generated HTML has no broken internal links or duplicate IDs.
- Image-bearing outputs embed figures and inline images as `data:image` URIs.
- Footnote ref, floating note, and fallback counts match when fallback notes are
  used.
- Known OCR/text-layer artifacts are scanned and absent.
- Metadata, copyright, catalog, and other omitted pages do not leak into reading
  text.
- Reading blocks have stable annotation anchors.
- Standard outputs include the fixed side navigator, in-body linked contents,
  draggable width control, reliable dashed separator at any text size or
  viewport width, active-link behavior, direct hash jumps, and no smooth
  scrolling.

## References

- `references/source-selection.md`
- `references/html-quality-bar.md`
- `references/figures-and-images.md`
- `references/footnotes-and-anchors.md`
- `references/text-cleanup.md`
- `references/existing-books.md`
