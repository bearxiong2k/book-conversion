# Figures And Images

Final generated HTML should be self-contained. Figures and inline images should
render from `data:image` URIs, while source assets remain regeneration inputs.

## Extraction

Audit PDF images with `page.get_images(full=True)` and
`page.get_image_rects(xref)`. Check `page.get_drawings()` when vector diagrams,
formulas, or line art may be present.

Filter by page context and area so tiny glyph fragments, decorations, or
publisher marks do not become figures.

## EPUB Assets

Use EPUB image assets when they are cleaner than PDF crops. Copy or extract them
with deterministic names into a book-local asset directory, then embed them into
the generated HTML with `image_file_to_data_uri`.

If EPUB provides both MathML/text and a rendered image fallback for the same
formula or diagram, render one visible representation. Prefer the image fallback
when the PDF layout is the authority.

## Validation

For image-bearing outputs, run validation with
`--require-self-contained-images`. The validator rejects external image paths,
malformed data URIs, and empty image payloads.

Use browser checks when natural dimensions, label legibility, or table/diagram
scale could fail after width or text-size changes.
