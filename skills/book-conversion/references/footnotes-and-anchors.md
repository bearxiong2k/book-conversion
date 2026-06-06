# Footnotes And Anchors

Footnotes and annotation anchors should be explicit and auditable.

## Footnotes

Prefer stable nearby target strings or real PDF superscript span metadata. Do
not rely only on visible note numbers when OCR or text-layer errors can corrupt
labels.

Converters should fail loudly or record a validation failure when a note target
cannot be found. Do not silently drop notes.

Drop extracted note paragraphs from body elements before merging paragraph
continuations. Otherwise notes can sit between two body fragments that should
join.

Validation should compare:

- visible note references;
- floating or hover notes;
- fallback list items when used;
- `fnref-*` and `fn-*` anchors.

Some outputs intentionally omit fallback note lists, but that should be captured
in the existing-book status or validation metadata.

## Annotation Anchors

Every generated book HTML should expose stable block-level anchors for external
annotation systems. `wrap_html_document` calls `add_annotation_anchors`
automatically.

The convention is:

- authored headings keep existing section IDs and receive `data-anchor-id`;
- paragraph-like blocks without IDs receive deterministic `ann-...` IDs;
- generated IDs are scoped to the nearest section and based on normalized block
  text;
- generated IDs are real `id` attributes as well as `data-anchor-id`.
