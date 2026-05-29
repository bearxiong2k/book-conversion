# PDF-to-HTML Conversion Case Study

Source: `Enjoy Your Symptom!_ Jacques Lacan in Hollywood and Out.pdf`  
Supplement: `Enjoy your symptom!_ Jacques Lacan in Hollywood and out_ -- Lacan, Jacques;Žižek, Slavoj -- Taylor & Francis (Unlimited), New York, 2008 -- Taylor and -- isbn13 9780203825402 -- 29b679f8326adec39685d378f55b08b8 -- Anna’s Archive.epub`  
Output: `enjoy-your-symptom.html`  
Generator: `convert_book.py`

This conversion follows the same reproducible pattern as the two reference projects: the final HTML is generated from the PDF, not hand-edited.

## Goals

- Convert the readable book content into a single selectable HTML edition.
- Exclude blank, promotional, series, and copyright/catalog pages.
- Preserve title page, contents, chapter hierarchy, section headings, paragraphs, italics, subscripts, index text, and endnotes.
- Convert superscript note references into hover footnotes with a fallback footnote list.
- Recover meaningful diagrams and stills from the EPUB where the PDF text extraction skips image blocks.
- Keep text corrections in the generator so the output can be regenerated safely.

## Extraction Method

- PyMuPDF is used through the local dependency path when available.
- The PDF text layer is good enough to avoid full OCR.
- Blocks are sorted by page position, with `NOTES` blocks splitting mixed body/note pages.
- Superscript note references are detected from real PDF span metadata, so Lacanian subscripts like `S1-S2` are preserved as subscripts instead of being mistaken for notes.
- Chapter notes are parsed section-wise from the book's endnote pages and matched back to body references by chapter.
- The EPUB is used as a cross-check source, not as the main body source: it preserved the structured index and figures, but shared several OCR/text-layer errors with the PDF.
- The EPUB index replaces the PDF index extraction when available, preserving cleaner entry boundaries and italics.
- Meaningful EPUB images are extracted to `assets/figures/` and inserted according to the PDF image block positions; chapter-opener scans and decorative page images are omitted.
- The EPUB also exposed a dropped inline Lacanian symbol, repaired in the generated text as `S(Ⱥ)`.

## Page Map

- Title page: PDF page 3.
- Contents: PDF pages 5-6.
- Routledge Classics preface: PDF pages 7-14.
- Introduction: PDF pages 15-16.
- Chapter 1: PDF pages 18-36.
- Chapter 2: PDF pages 38-63.
- Chapter 3: PDF pages 64-93.
- Chapter 4: PDF pages 94-117.
- Chapter 5: PDF pages 118-148.
- Chapter 6: PDF pages 149-176.
- Index: PDF pages 177-189.

## Validation

Run:

```bash
python3 convert_book.py
```

Then check:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
html = Path("enjoy-your-symptom.html").read_text(encoding="utf-8")
class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=set(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if "id" in d: self.ids.add(d["id"])
        if tag == "a" and d.get("href", "").startswith("#"): self.hrefs.append(d["href"][1:])
p=P(); p.feed(html)
print("broken anchors:", sorted(set(p.hrefs)-p.ids))
print("note refs:", html.count('class="note-ref"'))
print("floating notes:", html.count('class="floating-note"'))
print("fallback notes:", html.count('<li id="fn-'))
print("figures:", html.count('class="book-figure"'))
PY
```

Current validation result:

- Broken anchors: `0`
- Note references: `263`
- Floating notes: `263`
- Fallback notes: `263`
- Figures: `8`

Browser verification was done through a temporary localhost server with Playwright. The generated page rendered correctly, and a sampled hover footnote opened with the expected note text.
