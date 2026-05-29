# How to Read Lacan Conversion Case Study

## Sources

- `How to Read Lacan (How to Read).epub`
- `How to Read Lacan_pdf.pdf`

## Strategy

The EPUB is the text authority. The PDF has a ClearScan text layer with spacing and OCR damage, while the EPUB preserves readable paragraphs, emphasis, note links, chronology, further reading, and index entries.

## Method

1. Omitted cover, title-page bitmap, chapter-number ornaments, duplicate compiled notes, series advertising, and copyright pages.
2. Rebuilt a simple Sublime-style text title page in code.
3. Parsed selected EPUB spine members into headings, paragraphs, epigraph blockquotes, chronology entries, further reading, index, and author bio.
4. Used each chapter's local notes section as the source for footnotes, then replaced note references with hover popovers and fallback notes.
5. Normalized EPUB-only anchors such as `filepos...` into clean generated note IDs.
6. Generated contents and the fixed expandable navigator from final headings with the shared `SUBLIME_BOOK_CSS` and `render_sublime_nav`.

## Validation

Run after regeneration:

```bash
cd how-to-read
python3 convert_book.py
cd ..
python3 -m book_conversion_toolkit validate-html how-to-read/how-to-read-lacan.html \
  --expect-note-refs 60 \
  --expect-figures 0 \
  --scan calibre \
  --scan filepos \
  --scan "How to Read Lacan How to Read Lacan" \
  --scan "scroll-behavior" \
  --scan "\\bamella\\b" \
  --scan llamella \
  --scan "dano ferentes"
```

Current validation result:

- Broken anchors: `0`
- Duplicate IDs: `0`
- Figures: `0`
- Note references: `60`
- Floating notes: `60`
- Fallback notes: `60`
