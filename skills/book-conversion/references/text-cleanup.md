# Text Cleanup

Text cleanup should be deterministic, source-specific, and validated.

## Replacement Dictionaries

Use replacement dictionaries for recurring source errors. Keep them near the
book converter unless the rule is clearly reusable across books.

Separate concerns when practical:

- glyph or OCR corruption;
- typography and spacing;
- foreign or source-language terms;
- post-render markup fixes;
- artifact scan patterns.

Avoid global language rules for errors that are specific to one scan, EPUB, or
PDF text layer.

## Paragraph Merging

For PDF block extraction, run prose fragments through
`merge_continuation_paragraphs` before annotation anchors are assigned. Validate
PDF block-based prose with `--reject-split-paragraphs` when accidental page or
block splits are likely.

Paragraph joining should consider sentence closure, indentation, headings, note
removal, and page boundaries. Revisit raw extracted text when a paragraph looks
wrong; the cause may be corrupt source text rather than a bad join heuristic.

## Artifact Scans

Every high-confidence recurring error should have a scan pattern in validation.
Artifact scans should fail visibly when a known OCR/text-layer problem returns or
when omitted metadata leaks into reading text.
