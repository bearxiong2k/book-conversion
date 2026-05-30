# Case Lessons

## Source Selection

EPUB can be the best text authority when its spine is complete and preserves reading order. It may still have misleading navigation entries or missing end matter, so inspect the package rather than trusting the table of contents.

PDF text layers are useful when span metadata preserves italics, bold, and superscript note markers. They are risky when glyph corruption affects names, non-English terms, formulas, or footnote labels.

OCR is justified when the PDF text layer is worse than the OCR. Cache OCR page text under `tmp/ocr/` so repeated cleanup iterations do not rerun Tesseract.

Hybrid conversion is normal: one source may provide body text, another figures, another index structure, and another footnote layout.

## Structure

Create a page map before extracting full text. Print the first visible lines per page, identify title, contents, chapter starts, notes, index, and pages to omit.

Keep book-specific configuration local to each converter:

- page ranges and omitted pages;
- visible heading strings;
- cleanup replacement dictionaries;
- foreign/source-language term lists;
- footnote target strings;
- figure placement maps.

Keep reusable mechanics in `book_conversion_toolkit`:

- whitespace cleanup and line joining;
- stable section ID generation;
- annotation anchor insertion for external note apps;
- PDF positioned line extraction;
- EPUB spine/member reading;
- HTML wrapping, nav, and footnote rendering;
- validation.

## Annotation Anchors

Every generated book HTML should expose stable block-level anchors for external annotation systems. Use `wrap_html_document`, which calls `add_annotation_anchors` automatically. If a converter assembles the full document manually, run `add_annotation_anchors(markup)` just before writing the file.

The convention is:

- authored headings keep their existing section IDs and also receive `data-anchor-id`;
- paragraph-like reading blocks without IDs receive deterministic IDs shaped like `ann-{section}-{tag}-{hash}`;
- the hash is based on normalized block text and scoped to the nearest section, so unrelated edits elsewhere in the book do not shift anchors;
- generated IDs are real `id` attributes as well as `data-anchor-id`, making them usable by hash links and annotation stores.

## Footnotes

Prefer explicit, auditable note insertion. The best target is stable nearby body text or real PDF superscript span metadata. Do not rely only on visible numbers when OCR/text-layer degradation can turn labels into similar-looking symbols.

The converter should raise or record a failure when a note target cannot be found. Validation should compare:

- visible note refs;
- hover/floating notes;
- fallback list items;
- `fnref-*` and `fn-*` anchors.

Drop extracted note paragraphs from body elements before merging paragraph continuations. Otherwise notes can sit between two body fragments that should join.

## Figures

Audit PDF images with `page.get_images(full=True)` and `page.get_image_rects(xref)`, plus `page.get_drawings()` when formulas or vector diagrams may be present. Filter by area and context so tiny embedded word fragments are not treated as figures.

When EPUB images are cleaner than PDF crops, copy them reproducibly into `assets/figures/` and place them according to PDF or EPUB reading position.

After generation, validate that every `<img>` target exists and has nonzero bytes. Use browser checks for natural dimensions when image encoding is suspicious.

## Text Accuracy

Treat recurring OCR artifacts as source-specific corrections, not global language rules. Scan for the exact bad forms after every regeneration.

Foreign philosophical and psychoanalytic terms often need both character recovery and typographic treatment. Keep term emphasis lists separate from spelling corrections so validation can check each concern independently.

Paragraph joining should use several signals: indentation, previous sentence closure, headings, note removal, and page boundaries. Revisit raw extracted text when a paragraph looks wrong; the cause may be corrupt source text rather than the join heuristic.
