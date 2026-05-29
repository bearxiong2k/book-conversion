# EPUB/PDF-to-HTML Conversion Case Study

Primary source: `A Clinical Introduction to Lacanian Psychoanalysis_ Theory.epub`  
Reference source: `A Clinical Introduction to Lacanian Psychoanalysis_ Theory.pdf`  
Output: `a-clinical-introduction-to-lacanian-psychoanalysis.html`  
Generator: `convert_book.py`

This conversion prioritizes readable, selectable HTML text over page-image fidelity. The first pass used the local PDF text layer, but the current pass uses the supplied EPUB as the authority for text order, chapter completion, and inline figure placement. The EPUB contains the full chapter 10 ending that was missing from the PDF extraction. Its navigation file includes an `Afterword` entry, but the EPUB package does not contain a separate afterword or end-matter document; that entry points at the final chapter split.

## Workflow

1. Installed local conversion dependencies under `.codex_deps/`.
2. Parsed the EPUB `content.opf` spine to preserve reading order.
3. Inserted the chapter and part headings explicitly because the EPUB navigation labels are offset from the visible split contents.
4. Copied the EPUB cover and inline images into `assets/figures/` and inserted them in source order.
5. Rendered visible EPUB section headings as HTML headings and retained epigraphs as blockquotes.
6. Added targeted cleanup rules for Lacanian terms, French/German terms, broken hyphenation, and flattened dash joins found during EPUB comparison.
7. Generated a single self-contained HTML reading page with a fixed desktop navigation rail and responsive mobile layout.

## Validation

Commands run after regeneration:

```bash
python3 convert_book.py
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, '.codex_deps')
from bs4 import BeautifulSoup
html = Path('a-clinical-introduction-to-lacanian-psychoanalysis.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'lxml')
ids = {tag.get('id') for tag in soup.find_all(id=True)}
links = [a.get('href', '')[1:] for a in soup.find_all('a') if a.get('href', '').startswith('#')]
print(len(soup.find_all('p')), len(soup.find_all('figure')), len(soup.find_all(['h1', 'h2', 'h3'])))
print([href for href in links if href not in ids])
PY
rg -n "Chapter are|flesh - and|run-of-themill|stress related”which|tclling|want-tobe|herself”What|lives”Now|dtfense|jonissance|l\\.acan|DSM-Ill|Ecrits|someThing|and and every" a-clinical-introduction-to-lacanian-psychoanalysis.html
```

Browser validation through a temporary local server confirmed:

- 30 figures load with nonzero natural dimensions.
- 57 total headings render, including the title.
- Navigation anchors resolve.
- Desktop navigation does not overlap the reading column.

## Known Limitations

- The supplied EPUB package does not include a distinct afterword, recommended reading section, notes, or index document despite the generic navigation entry.
- Footnote markers are preserved as source text, but no corresponding note section is present in the EPUB package.
- The EPUB text contains scan artifacts; cleanup rules cover the high-confidence recurring artifacts found during validation, but this remains a script-assisted migration rather than a manually proofread scholarly edition.
