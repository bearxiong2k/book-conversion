# Book Conversion Project Guidance

Use the local `book-conversion` skill for future conversions. Its source lives at `skills/book-conversion/SKILL.md`.

Core rules:

- Keep generated HTML reproducible from a converter script. Do not hand-edit final HTML without encoding the fix in the generator.
- Put shared logic in `book_conversion_toolkit/`; keep book-specific page maps, source corrections, and footnote targets in each book sub-project.
- Prefer root dependencies in `.codex_deps/` using `scripts/bootstrap_deps.sh`; avoid adding another per-book dependency folder unless isolation is necessary.
- Validate after regeneration with `python3 -m book_conversion_toolkit validate-html ...` or `python3 scripts/validate_existing_outputs.py`.
- For scanned or corrupt text layers, compare PDF text extraction against OCR and EPUB when available before committing to an extraction strategy.
- Preserve user/book-specific corrections as deterministic dictionaries and explicit target matches so missing notes or shifted text fail visibly.
