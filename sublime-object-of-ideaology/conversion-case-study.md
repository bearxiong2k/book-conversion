# PDF-to-HTML Conversion Case Study

Example source: `The Sublime Object of Ideology.pdf`  
Output: `the-sublime-object-frontmatter.html`  
Generator: `convert_frontmatter.py`

This case records the method used to convert a scanned/text-layer PDF book into an accurate, readable HTML edition with hover footnotes and recovered figures.

## Goals

- Convert only the intended reading content, excluding metadata/copyright/catalog pages.
- Preserve title page, table of contents, preface, introduction, chapter text, headings, footnotes, figures, and important formulas.
- Use selectable HTML text rather than page screenshots for body content.
- Provide a left-side navigator for desktop reading, including parts, chapters, sections, and subsections.
- Render footnotes as hover popovers: hovering the note number opens a fixed floating box near the reference, and the note remains selectable.
- Keep the process reproducible through a generator script instead of hand-editing the final HTML.

## Tools Used

- PyMuPDF (`fitz`) for PDF text extraction, page/block inspection, and embedded image extraction.
- Tesseract/visual checks where the PDF text layer looked suspicious.
- Local Python scripts for validation:
  - HTML parse check.
  - footnote-reference-to-note consistency.
  - OCR artifact scans.
  - metadata leakage checks.
- Playwright browser checks for:
  - hover footnote behavior.
  - expandable navigator behavior and anchor targets.
  - figure image loading.
  - generated page sanity.

## High-Level Workflow

1. Map PDF page indexes to book sections.
2. Extract text by block, filtering out page headers, footers, page numbers, and note blocks.
3. Apply targeted OCR/text-layer replacements.
4. Insert section headings and paragraph breaks using known heading strings plus paragraph starter heuristics.
5. Insert footnotes explicitly by matching nearby source text.
6. Extract real embedded figures from the PDF and place them at the corresponding headings or formula/schema references.
7. Assign stable IDs to generated section/subsection headings.
8. Build the left navigator from the final heading list.
9. Regenerate HTML from the script.
10. Run validators and browser checks.
11. Iterate when validation or visual checks find missing markers, bad OCR, broken navigation, or missing figures.

## Page and Section Mapping

A reliable page map was built first. For this book:

- Front matter, preface, and introduction were extracted first.
- Chapter 1 began at PDF index 33.
- Chapter 2 began at PDF index 87.
- Chapter 3 began at PDF index 125.
- Chapter 4 began at PDF index 175.
- Chapter 5 began at PDF index 201.
- Chapter 6 began at PDF index 257.
- Index began at PDF index 295 and was not included.

The exact page indexes were confirmed by printing the first visible lines of each PDF page and checking chapter-title pages.

## Text Extraction Strategy

Text was extracted from sorted PDF blocks:

- Sort blocks by `(y, x)` coordinates.
- Drop top headers on non-title pages.
- Drop bottom footnote/page-footer areas from body extraction.
- Drop lines that are only running heads, page numbers, or chapter headings already represented structurally.
- Join lines carefully, removing soft hyphen breaks.

This was more reliable than plain full-page text extraction because the PDF contained:

- corrupted glyphs,
- word fragments,
- footnotes mixed into body flow,
- repeated running headers,
- embedded image fragments for some italic words and symbols.

## OCR/Text-Layer Cleanup

The PDF text layer was noisy. Cleanup was handled through a `REPLACEMENTS` dictionary in the generator.

Examples of recurring corrections:

- `Ideolo8ical` -> `Ideological`
- `partidpants` -> `participants`
- `PhellomellologyofSpin't` -> `Phenomenology of Spirit`
- `oflanguage` -> `of language`
- `nothil18` -> `nothing`
- `positi118` -> `positing`
- `presupposi118` -> `presupposing`

Important lesson: do not assume a bad paragraph is caused only by paragraph joining. In this case, one user-reported bad paragraph came from a corrupt PDF text layer plus missing page-specific cleanup rules. The fix was to inspect the raw page text, add targeted replacements, and ensure the heading was separated.

## Footnote Method

Footnotes were inserted chapter-by-chapter using explicit dictionaries:

- `FOOTNOTES`
- `INTRO_FOOTNOTES`
- `CHAPTER_ONE_FOOTNOTES`
- etc.

Each note was inserted by matching nearby source text rather than by blindly trusting numeric markers, because the PDF text layer often degraded markers:

- `10` became `'o`
- `11` became `!l`
- `2` became `z`
- `25` became `2S`

The generator raises an error if a footnote marker target cannot be found. This made missing or shifted notes visible immediately.

The HTML footnote structure uses:

- a reference `sup.note-ref`,
- a sibling `.floating-note`,
- JavaScript to position the note near cursor/focus,
- hover/focus handlers that keep the note open when moving from reference into the popup.

Validation always checked:

- every `fnref-*` has a matching `fn-*`,
- every `fn-*` has a matching `fnref-*`,
- chapter note counts match expectations.

## Figure and Formula Audit

After the text conversion, the PDF was scanned for embedded images:

```python
page.get_images(full=True)
page.get_drawings()
```

This found both meaningful figures and non-meaningful tiny fragments. The meaningful figures were:

- Chapter 3: `Graph I`
- Chapter 3: `Graph II`
- Chapter 3: `Graph III`
- Chapter 3: `Completed Graph`
- Chapter 5: `Schema from Seminar Encore`

Tiny embedded images such as isolated italic words, punctuation, or single characters were treated as PDF/OCR artifacts and not inserted as standalone figures.

Meaningful figures were extracted reproducibly into:

```text
assets/figures/
```

The generator inserts them with `<figure>`, `<img>`, and `<figcaption>` blocks.

Browser validation confirmed each inserted image loaded with nonzero natural dimensions.

## HTML Structure

The final HTML is generated as one file with:

- a fixed desktop left navigator,
- semantic sections,
- title page,
- contents,
- part headings,
- chapter headings,
- subheadings,
- paragraphs,
- bullet paragraphs,
- figure blocks,
- hidden desktop endnote list for fallback/mobile use,
- hover popover notes on desktop.

Navigator behavior:

- Desktop/wide screens: a fixed left rail is shown beside the reading column.
- The navigator is generated from actual `h2`, `h3`, and `h4` elements rather than from a separate hand-maintained list.
- Parts and chapters are expandable with native `<details>` and `<summary>`.
- Chapters include an overview link plus nested section and subsection links.
- Generated `h3` and `h4` headings receive stable slug IDs so every navigator entry has an anchor target.
- Narrow screens hide the navigator to preserve the reading column.

Footnote list behavior:

- Desktop: endnote list hidden; hover popovers are primary.
- Mobile/narrow screens: popovers hidden; footnote list shown.

## Validation Checklist

Run after every significant regeneration:

1. HTML parse check.
2. Footnote reference consistency:
   - count refs,
   - count notes,
   - list missing refs,
   - list extra notes.
3. Metadata exclusion check:
   - `ISBN`
   - `Library of Congress`
   - `copyright`
   - `British Library`
4. Chapter-specific OCR artifact scan:
   - digit-letter blends,
   - known corrupted glyphs,
   - broken headings,
   - leaked raw note markers.
5. Figure scan:
   - expected `<figure>` count,
   - expected image filenames present,
   - assets exist on disk.
6. Navigator scan:
   - every nav `href` resolves to an element,
   - generated `h3`/`h4` headings have IDs,
   - expandable groups are present,
   - nav does not overlap the reading column.
7. Browser checks:
   - note hover opens a fixed floating box,
   - note text is correct,
   - navigator renders beside the text on desktop,
   - figures load with natural width/height.

## Common Failure Modes

- Footnotes leaking into body text because the bottom cutoff is too low.
- Body text lost because the bottom cutoff is too aggressive.
- Running headers mistaken for content.
- Chapter title pages needing different top cutoff rules.
- Numeric footnote markers degraded by OCR.
- Figures missed because they are embedded as PDF images while surrounding captions are text.
- Tiny embedded word fragments mistaken for figures.
- Heading detection failing because a corrupted heading was not normalized first.
- Navigator drift if links are hand-maintained separately from generated headings.
- Duplicate or unstable heading IDs if generated only from visible text without collision handling.
- Left navigation overlapping the reading column unless desktop layout reserves enough horizontal space.
- Paragraph splitting producing very long paragraphs unless starter heuristics are added.

## Recommended Future Process

For future books, use this order:

1. Create a page map before conversion.
2. Build one extraction function per logical section/chapter.
3. Keep text cleanup centralized in a replacement dictionary.
4. Insert footnotes with explicit target strings and fail loudly when a marker is missing.
5. Add validators before expanding to the next chapter.
6. Audit figures/formulas after text and footnotes are stable.
7. Generate navigation from the final heading structure, not from a duplicate outline.
8. Keep all generated assets under a predictable directory.
9. Use browser automation to verify interactive behavior, navigation anchors, and asset loading.

The key principle is to make conversion script-driven and auditable. Manual correction is acceptable only when it is encoded back into the generator, so the final HTML can be regenerated without losing fixes.
