# PDF-to-HTML Conversion Case Study

Example source: `Edmund Husserl (auth.) - The Idea of Phenomenology_ A Translation of Die Idee der PhÃ¤nomenologie Husserliana II-Springer Netherlands (1999).pdf`  
Output: `the-idea-of-phenomenology.html`  
Generator: `convert_book.py`

This case records the method used to convert a text-heavy philosophy PDF into a readable, selectable HTML edition where text accuracy is the first priority.

## Goals

- Convert the book into a single HTML file with selectable body text.
- Preserve title page, contents, headings, paragraphs, page-reference brackets, index text, and notes.
- Exclude non-reading front matter such as half-title, series, and copyright pages.
- Render footnotes as hover popovers, with a fallback footnote list.
- Keep the output reproducible through a generator script rather than hand-editing the HTML.
- Treat foreign-language philosophical terms carefully, especially German and Greek terms.

## Tools Used

- PyMuPDF (`fitz`) for PDF inspection and page rendering.
- Tesseract OCR for body-text extraction where the PDF text layer was unreliable.
- TSV extraction for index pages, because the index needed column-preserving treatment.
- Local Python validation scripts for HTML parsing, footnote consistency, paragraph-flow checks, and OCR artifact scans.
- Browser/Playwright validation for hover-footnote behavior.

## High-Level Workflow

1. Render and OCR PDF pages into `tmp/ocr/`.
2. Omit known non-reading pages through `OMIT_PAGES`.
3. Extract index pages separately through Tesseract TSV into `tmp/index_tsv/`.
4. Remove running headers, page numbers, and repeated book furniture.
5. Normalize OCR output with a targeted `REPLACEMENTS` dictionary.
6. Split OCR text into structural elements: title page, contents, headings, paragraphs, notes, and index blocks.
7. Drop extracted raw note paragraphs before paragraph-continuation merging.
8. Merge paragraph continuations across page boundaries when the preceding paragraph clearly lacks sentence closure.
9. Insert curated footnotes by matching stable nearby source text.
10. Emphasize German, Greek, and other source-language terms with `<em>`.
11. Regenerate the HTML and run validation checks.

## Text Extraction Strategy

OCR was preferred for the body because the text layer contained enough glyph corruption to damage philosophical terms. The converter stores the OCR cache so later iterations can focus on cleanup rules and rendering logic without rerunning expensive OCR.

The converter uses page-level cleanup before structural parsing:

- remove running headers and page numbers;
- normalize known OCR mistakes;
- preserve page-reference markers like `[36]`;
- join wrapped lines while respecting intended hyphenated compounds;
- keep the index on a separate path so two-column index text is not treated as ordinary prose.

## Paragraph Merging Lesson

A user-reported case showed this sentence split incorrectly:

```text
... how to explain the prejudice that
ascribes a transcendent accomplishment to knowledge. This is the way Hume took.
```

The problem was not just a paragraph-merging heuristic. Extracted note paragraphs were sitting between body paragraphs, so page-continuation logic could not see that two adjacent body paragraphs belonged together.

The fix was to drop extracted note text before running `merge_continuations()`:

```python
elements = drop_extracted_notes(elements)
elements = merge_continuations(elements)
```

Validation then checked that known continuation phrases appear inside a single parsed paragraph:

- `Where do we look for help then? We proceed to assess`
- `Indeed, the real meaning of logical lawfulness`
- `how to explain the prejudice that ascribes`

## Footnote Method

Footnotes are represented in `FOOTNOTES` with:

- a stable identifier;
- a visible note label;
- note text;
- a source-text target near the reference;
- an optional section ID.

The generator inserts a hover footnote immediately after the matched target text. The HTML structure uses:

- `sup.note-ref` for the visible note number;
- `.floating-note` for the popover note;
- a fallback `<section class="footnotes">` list for narrow screens and accessibility;
- JavaScript to keep notes open while moving from the reference into the popover.

Validation checked:

- 11 note references;
- 11 hover popovers;
- 11 fallback list items;
- no broken footnote anchors;
- no raw `ENDNOTES` or extracted note paragraphs leaking into the body.

## Foreign-Language and OCR Cleanup

German and Greek terms required two different treatments:

1. Correct corrupted OCR into the intended source text.
2. Emphasize source-language terms with `<em>`.

Examples of targeted OCR replacements:

- `Phanomenoiogie` -> `Phänomenologie`
- `natiirliche Wissenschaften` -> `natürliche Wissenschaften`
- `Jiirgen Sander` -> `Jürgen Sander`
- `Seefelder Blatter` -> `Seefelder Blätter`
- `pet&Paors\neis &AAO ‘yévos` -> `μετάβασις εἰς ἄλλο γένος`
- `(pawOpevov` -> `φαινόμενον`

Examples of emphasized source terms:

- `Die Idee der Phänomenologie`
- `Ding und Raum`
- `Husserl-Chronik`
- `natürliche Wissenschaften`
- `positive Wissenschaften`
- `Sinn`
- `Bedeutung`
- `Erkenntnis`
- `reell`, `reelle`, `reellen`, `reeller`, `reelles`
- `μετάβασις εἰς ἄλλο γένος`
- `φαινόμενον`

Important lesson: non-English philosophical terms should not be handled only as spelling corrections. They often need both accurate character recovery and typographic marking.

## HTML Structure

The generated HTML is a single self-contained file with:

- fixed left navigation on wide screens;
- centered reading column;
- title page;
- contents;
- section headings with stable IDs;
- paragraphs;
- index columns;
- hover footnotes;
- mobile fallback footnote list.

Foreign terms are emphasized after HTML escaping and after footnotes are inserted, so the same emphasis logic applies to body text, titles, and note text.

## Validation Checklist

Run after every significant regeneration:

1. Regenerate:

```bash
python3 convert_book.py
```

2. Scan for known OCR leftovers:

```bash
rg -n "AAO|yévos|pet&|pet&amp;|natiirliche|Jiirgen|Blatter|Phanomen|metabasis eis" the-idea-of-phenomenology.html
```

3. Check footnote integrity:

- count note references;
- count hover popovers;
- count fallback list items;
- verify every `href="#..."` resolves to an element ID.

4. Check paragraph continuations by parsing `<p>` elements and searching for known joined phrases.

5. Check raw-note leakage:

```bash
rg -n "ENDNOTES|NOTES TO|The numbers in brackets refer|See Addendum|In the manuscript" the-idea-of-phenomenology.html
```

6. Check foreign-term emphasis by stripping `<em>...</em>` spans and scanning for important source terms that remain plain.

7. Browser-check at least one hover footnote after changes to note markup, CSS, or JavaScript.

## Common Failure Modes

- OCR splits a source-language phrase across lines before normalization.
- A partial OCR replacement changes only the first token, leaving the rest of a Greek/German phrase corrupt.
- Extracted note paragraphs interrupt page-continuation merging.
- Footnote markers work in the body but the fallback list has broken backrefs.
- German terms appear with ASCII OCR substitutions such as `ii` for `ü`.
- Index pages need different extraction logic from body prose.
- Validation scripts that look for old CSS class names can undercount footnotes after markup changes.
