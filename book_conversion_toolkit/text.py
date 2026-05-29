from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Mapping, MutableMapping, MutableSet, Sequence


def apply_replacements(text: str, replacements: Mapping[str, str] | None = None) -> str:
    """Apply deterministic source-to-target replacements in insertion order."""

    if not replacements:
        return text
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def clean_spaces(text: str, replacements: Mapping[str, str] | None = None) -> str:
    """Normalize common PDF/OCR whitespace without changing semantic punctuation."""

    text = text.replace("\ufeff", "").replace("\x0c", "").replace("\u00ad", "")
    text = apply_replacements(text, replacements)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    text = re.sub(r"([([{])\s+", r"\1", text)
    text = re.sub(r"\s+([])}])", r"\1", text)
    text = re.sub(r"\s+([”’])", r"\1", text)
    text = re.sub(r"([“‘])\s+", r"\1", text)
    return text.strip()


def looks_sentence_closed(text: str) -> bool:
    """Return true when a line/paragraph probably ends a prose sentence."""

    return bool(re.search(r"[.!?;:][\"'”’)]*$", text.strip()))


def _hyphen_prefix(text: str) -> str:
    match = re.search(r"([A-Za-z]{2,})-$", text)
    return match.group(1).lower() if match else ""


def join_wrapped_lines(
    lines: Sequence[str],
    replacements: Mapping[str, str] | None = None,
    keep_hyphen_prefixes: set[str] | None = None,
) -> str:
    """Join extracted lines into prose, treating terminal hyphens as soft by default.

    `keep_hyphen_prefixes` is for real compounds such as "self-" or "non-".
    """

    out = ""
    for raw_line in lines:
        line = clean_spaces(raw_line, replacements)
        if not line:
            continue
        if not out:
            out = line
            continue
        if out.endswith("-"):
            prefix = _hyphen_prefix(out)
            if keep_hyphen_prefixes and prefix in keep_hyphen_prefixes:
                out += line
            else:
                out = out[:-1] + line
        else:
            out += " " + line
    return clean_spaces(out, replacements)


def slugify(
    text: str,
    used: MutableSet[str] | MutableMapping[str, int] | None = None,
    fallback: str = "section",
) -> str:
    """Create a stable ASCII HTML id and avoid collisions when `used` is provided."""

    value = html.unescape(text)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("'", "").replace("’", "")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-") or fallback

    if used is None:
        return value

    if isinstance(used, MutableMapping):
        count = used.get(value, 0)
        used[value] = count + 1
        return value if count == 0 else f"{value}-{count + 1}"

    candidate = value
    index = 2
    while candidate in used:
        candidate = f"{value}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def escape_text(text: str) -> str:
    return html.escape(text, quote=False)
