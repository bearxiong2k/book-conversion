# HTML Quality Bar

Generated HTML should be portable, selectable, navigable, and reproducible. Fix
problems in the converter or toolkit, not by editing generated HTML.

## Standard Shell

Standard book outputs should use:

- `render_standard_nav` for the fixed side navigator;
- `render_linked_contents` for in-body contents;
- `STANDARD_BOOK_CSS` for shared typography and layout;
- `wrap_html_document` for the shell, nav behavior, scripts, and annotation
  anchors.

Validation with `--require-standard-nav` checks the fixed nav shell, linked
contents, resizer, reopen button, active-link behavior, hash-change handling,
details expansion, animation-frame throttling, disabled overscroll, and absence
of smooth scrolling.

## Width And Text Size

Reading width should be freely adjustable by default. Do not lock the whole book
to a fixed PDF-like column unless a specific element would fail. When dense
figures, diagram labels, tables, formulas, or captions need constraints, scope
the constraint to that element or section.

The side navigator must remain reachable after larger text-size settings and
reading-width changes. Browser-check collapse and reopen behavior when touching
standard nav CSS or JavaScript. This is a known risk for `the-lacanian-subject`.

## Browser Checks

Use browser or Playwright checks when changing:

- shared CSS or nav JavaScript;
- hover notes or fallback note behavior;
- figures, formulas, MathML, or image fallback handling;
- mobile or narrow viewport behavior;
- text-size and width controls.

Direct hash jumps should work without smooth scrolling. Details groups in the
navigator should open automatically for active links.
