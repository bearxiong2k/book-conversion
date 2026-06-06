# Source Selection

Choose the body-text authority before building the full converter. Inspect the
available sources, then document the decision in the converter or validation
metadata.

## EPUB

Use EPUB when its spine is complete, ordered, and preserves paragraphs, tables,
MathML, note links, and image assets. Do not trust the table of contents alone;
inspect the OPF spine and actual members.

EPUB can still be wrong about layout. Cross-check chapter openings, figures,
tables, and formulas against the PDF when the PDF is the typographic authority.

## PDF Text Layer

Use the PDF text layer when positioned spans preserve usable reading order,
italics, bold, superscript note markers, and formulas. It is risky when glyph
corruption affects names, foreign terms, note labels, or mathematical symbols.

Map pages first with:

```bash
python3 -m book_conversion_toolkit inspect-pdf "book.pdf" --pages 1-20 --lines 8
```

## OCR

Use OCR when the PDF text layer is worse than OCR. Cache OCR output under a
book-local `tmp/ocr/` directory so cleanup iterations do not rerun Tesseract.

Keep OCR corrections source-specific. Recurring errors should become replacement
dictionaries plus artifact scans.

## Hybrid

Hybrid conversion is normal. One source may provide body text, another figures,
another note layout, and another index structure. Keep the decision explicit so
future maintainers know why the converter uses multiple authorities.
