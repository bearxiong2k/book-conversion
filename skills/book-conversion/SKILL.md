---
name: book-conversion
description: Convert scholarly/theory books from PDF, EPUB, or OCR into reproducible single-file HTML editions with selectable text, navigation, figures, footnotes, validation, and reusable cleanup logic. Use for future book conversion projects based on the examples in this repository.
---

# Book Conversion

Use this skill when converting books like the four repository examples into readable, selectable HTML. The quality bar is script-driven reproducibility: every correction, omission, figure, footnote, and heading decision belongs in code or documented configuration, not in manual edits to generated HTML.

## Start

1. Read the relevant prior case studies:
   - `clinical-intro/conversion-case-study.md` for EPUB-authoritative conversion.
   - `enjoy-your-symptom/conversion-case-study.md` for PDF text-layer plus EPUB figures/index.
   - `the-idea-of-phenomenology/conversion-case-study.md` for OCR-first extraction and index TSV handling.
   - `sublime-object-of-ideaology/conversion-case-study.md` for noisy PDF text, explicit footnotes, and figure audit.
2. Bootstrap dependencies if the root `.codex_deps/` does not exist:

   ```bash
   bash scripts/bootstrap_deps.sh
   ```

3. In a new book sub-project, insert both paths before imports:

   ```python
   import sys
   sys.path.insert(0, "../.codex_deps")
   sys.path.insert(0, "..")
   ```

4. Use `book_conversion_toolkit` for shared text cleanup, slug generation, PDF line inspection, EPUB spine/member reads, footnote rendering, navigation rendering, and HTML validation.

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
8. Generate the nav from final headings, not a separate hand-maintained outline.
9. Regenerate and validate after each significant section.

## Toolkit Commands

Validate an output:

```bash
python3 -m book_conversion_toolkit validate-html output.html \
  --expect-note-refs 11 \
  --expect-figures 5 \
  --scan "known_bad_ocr"
```

Validate all current example outputs:

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

Use browser/Playwright checks when CSS, navigation, hover notes, mobile behavior, or figures changed.

## Detailed Lessons

Read `references/case-lessons.md` when choosing between PDF, EPUB, OCR, or hybrid extraction, or when debugging paragraph merging, note leakage, image extraction, or foreign-language term cleanup.
