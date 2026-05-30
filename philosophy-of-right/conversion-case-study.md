# Philosophy of Right Conversion Case Study

## Sources

- `Philosophy of Right.pdf`

## Strategy

The PDF text layer is usable and preserves the book's paragraph order better than OCR would. The converter therefore uses PyMuPDF extraction with deterministic cleanup, an explicit printed-contents page map, and the shared Sublime-style HTML infrastructure.

## Method

1. Omitted publisher, series, copyright, blank, and repeated title separator pages.
2. Rebuilt a simple title page in code.
3. Mapped the printed contents to generated headings and anchors, including front matter, the preface, nested book sections, explanatory notes, and index.
4. Inserted headings at their source heading lines when visible; delayed fallback headings past page-continuation paragraphs to avoid interrupting running text.
5. Classified smaller indented material as additions or explanatory note text, then merged page continuations across bottom notes without letting notes absorb main text.
6. Rendered linked contents and the fixed expandable navigator with the shared `SUBLIME_BOOK_CSS`, `render_linked_contents`, and `render_sublime_nav`.
7. Rendered the index as two-column preformatted blocks to preserve compact index line structure.

## Validation

Run after regeneration:

```bash
cd philosophy-of-right
python3 convert_book.py
cd ..
python3 -m book_conversion_toolkit validate-html philosophy-of-right/philosophy-of-right.html \
  --expect-figures 0 \
  --scan "This page intentionally" \
  --scan "Great Clarendon" \
  --scan "All rights reserved" \
  --scan "ﬁ" \
  --scan "ﬂ" \
  --scan "Contents vi" \
  --scan "scroll-behavior"
```

Current validation result:

- Broken anchors: `0`
- Duplicate IDs: `0`
- Figures: `0`
- Note references: `0`
- Floating notes: `0`
- Fallback notes: `0`
