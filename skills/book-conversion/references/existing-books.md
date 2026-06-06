# Existing Books

This table is the compact audit surface for current conversions. Detailed page
maps, footnote targets, replacement dictionaries, and figure maps stay in the
book converters or validation metadata.

| Book | Source authority | Converter | Output | Notes | Figures | Special checks |
| --- | --- | --- | --- | ---: | ---: | --- |
| `clinical-intro` | Hybrid PDF/EPUB | `clinical-intro/convert_book.py` | `clinical-intro/a-clinical-introduction-to-lacanian-psychoanalysis.html` | 0 | 30 | Deterministic figure extraction; self-contained images |
| `enjoy-your-symptom` | PDF body and notes, EPUB for comparison | `enjoy-your-symptom/convert_book.py` | `enjoy-your-symptom/enjoy-your-symptom.html` | 263 | 8 | Paragraph continuation validation |
| `the-idea-of-phenomenology` | OCR-heavy PDF workflow | `the-idea-of-phenomenology/convert_book.py` | `the-idea-of-phenomenology/the-idea-of-phenomenology.html` | 11 | 0 | OCR cache reproducibility; Greek/German correction scans |
| `sublime-object-of-ideaology` | PDF frontmatter and selected chapters | `sublime-object-of-ideaology/convert_frontmatter.py` | `sublime-object-of-ideaology/the-sublime-object-frontmatter.html` | 124 | 5 | Manual footnote maps; figure extraction; largest cleanup candidate |
| `for-they-know-not` | EPUB body, notes, and figures | `for-they-know-not/convert_book.py` | `for-they-know-not/for-they-know-not.html` | 371 | 11 | Omitted EPUB members stay omitted |
| `how-to-read` | EPUB body and notes | `how-to-read/convert_book.py` | `how-to-read/how-to-read-lacan.html` | 60 | 0 | Duplicate note chapter skipped |
| `philosophy-of-right` | PDF text layer | `philosophy-of-right/convert_book.py` | `philosophy-of-right/philosophy-of-right.html` | 163 | 0 | Publisher and metadata pages omitted |
| `the-lacanian-subject` | EPUB body, notes, index, and image fallbacks | `the-lacanian-subject/convert_book.py` | `the-lacanian-subject/the-lacanian-subject.html` | 246 | 73 | MathML/image fallback decisions; dashed separator opens side nav after larger text/125% and 150% zoom; no fallback note list expected |

Run the portable quality gate after regeneration:

```bash
python3 scripts/quality_gate.py
```

Validation metadata lives in `scripts/conversion_cases.py`.
