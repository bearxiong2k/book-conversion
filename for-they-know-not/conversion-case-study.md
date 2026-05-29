# EPUB/PDF-to-HTML Conversion Case Study

Primary source: `For They Know Not What They Do.epub`  
Reference source: `For They Know Not What They Do_Enjoyment as a political factor.pdf`  
Output: `for-they-know-not.html`  
Generator: `convert_book.py`

This first conversion uses the EPUB as the text authority. The PDF text layer was useful for sampling page structure, but it contains visible corruption such as damaged author names and headings. The EPUB preserves better Unicode text, a complete navigation map, inline note references, endnotes, index text, and images.

## Workflow

1. Inspected the PDF page starts with `book_conversion_toolkit inspect-pdf`.
2. Parsed the EPUB `toc.ncx` and `content.opf` to preserve reading order and navigation hierarchy.
3. Omitted cover duplicates, half-title, copyright, and the raw notes chapter from body flow.
4. Rendered a single title page from EPUB metadata and cover image.
5. Converted the EPUB nav map into stable HTML headings and a left navigation rail.
6. Parsed the notes chapter by source chapter and note number because note labels restart by section.
7. Replaced Unicode superscript note references with hover popovers and fallback footnotes.
8. Copied EPUB inline content images into `assets/figures/` in source order.
9. Preserved the EPUB index as structured paragraphs with indented subentries.
10. Matched the Sublime Object UI conventions: simple text title page, fixed expandable navigator, and direct anchor jumps without smooth scrolling.

## Validation

Run after regeneration:

```bash
python3 convert_book.py
cd ..
python3 -m book_conversion_toolkit validate-html for-they-know-not/for-they-know-not.html \
  --expect-figures 11 \
  --scan Roudedge \
  --scan direcdy \
  --scan detaded \
  --scan forgetten \
  --scan mouuement \
  --scan silendy \
  --scan Weatherhilt \
  --scan suiprising
```

Current validation result:

- Broken anchors: `0`
- Duplicate IDs: `0`
- Figures: `11`
- Note references: `371`
- Floating notes: `371`
- Fallback notes: `371`

## Known Limitations

- The EPUB itself contains some suspicious terms that may be intentional Lacanian typography rather than OCR errors, especially `Llanguage`. These were left unchanged.
- The pass is not a manual scholarly proofread. Cleanup rules cover recurring high-confidence source artifacts found during sampling and validation.
