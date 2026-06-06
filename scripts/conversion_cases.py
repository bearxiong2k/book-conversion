from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ValidationCase:
    slug: str
    output: Path
    converter: Path
    source_authority: str
    expected_figures: int | None = None
    expected_note_refs: int | None = None
    artifact_patterns: tuple[str, ...] = field(default_factory=tuple)
    require_standard_nav: bool = True
    reject_split_paragraphs: bool = False
    special_checks: tuple[str, ...] = field(default_factory=tuple)

    def output_path(self, root: Path) -> Path:
        return root / self.output


CASES: tuple[ValidationCase, ...] = (
    ValidationCase(
        slug="clinical-intro",
        output=Path("clinical-intro/a-clinical-introduction-to-lacanian-psychoanalysis.html"),
        converter=Path("clinical-intro/convert_book.py"),
        source_authority="Hybrid PDF/EPUB",
        expected_figures=30,
        artifact_patterns=(
            r"Chapter are",
            r"run-of-themill",
            r"dtfense",
            r"jonissance",
            r"DSM-Ill",
        ),
        special_checks=("figure extraction remains deterministic",),
    ),
    ValidationCase(
        slug="enjoy-your-symptom",
        output=Path("enjoy-your-symptom/enjoy-your-symptom.html"),
        converter=Path("enjoy-your-symptom/convert_book.py"),
        source_authority="PDF body and notes, EPUB available for comparison",
        expected_figures=8,
        expected_note_refs=263,
        artifact_patterns=(
            r"replusive",
            r"Englightenment",
            r"Idealogy",
            r"Kierkegaard's materialist r<",
        ),
        reject_split_paragraphs=True,
        special_checks=("paragraph continuation merging",),
    ),
    ValidationCase(
        slug="the-idea-of-phenomenology",
        output=Path("the-idea-of-phenomenology/the-idea-of-phenomenology.html"),
        converter=Path("the-idea-of-phenomenology/convert_book.py"),
        source_authority="OCR-heavy PDF workflow",
        expected_note_refs=11,
        artifact_patterns=(
            r"AAO",
            r"pet&amp;",
            r"natiirliche",
            r"Jiirgen",
            r"Phanomen",
        ),
        special_checks=("OCR cache reproducibility", "Greek and German correction scans"),
    ),
    ValidationCase(
        slug="sublime-object-of-ideaology",
        output=Path("sublime-object-of-ideaology/the-sublime-object-frontmatter.html"),
        converter=Path("sublime-object-of-ideaology/convert_frontmatter.py"),
        source_authority="PDF frontmatter and selected chapters",
        expected_figures=5,
        artifact_patterns=(
            r"Ideolo8ical",
            r"partidpants",
            r"Phellomellology",
            r"nothil18",
            r"copyright",
            r"ISBN",
            r"\[re\)production",
            r"t/z",
            r"΢",
            r"\bro (constrict|recognize|the)\b",
            r"overlook\)ng",
            r"evel\)lthing",
        ),
        special_checks=("manual footnote maps", "figure extraction"),
    ),
    ValidationCase(
        slug="for-they-know-not",
        output=Path("for-they-know-not/for-they-know-not.html"),
        converter=Path("for-they-know-not/convert_book.py"),
        source_authority="EPUB body, notes, and figures",
        expected_figures=11,
        expected_note_refs=371,
        artifact_patterns=(
            r"Roudedge",
            r"direcdy",
            r"detaded",
            r"forgetten",
            r"mouuement",
            r"silendy",
            r"Weatherhilt",
            r"suiprising",
            r"(?<!over)scroll-behavior",
        ),
        special_checks=("omitted EPUB members stay omitted",),
    ),
    ValidationCase(
        slug="how-to-read",
        output=Path("how-to-read/how-to-read-lacan.html"),
        converter=Path("how-to-read/convert_book.py"),
        source_authority="EPUB body and notes",
        expected_figures=0,
        expected_note_refs=60,
        artifact_patterns=(
            r"calibre",
            r"filepos",
            r"How to Read Lacan How to Read Lacan",
            r"(?<!over)scroll-behavior",
            r"\bamella\b",
            r"llamella",
            r"dano ferentes",
        ),
        special_checks=("duplicate note chapter skipped",),
    ),
    ValidationCase(
        slug="philosophy-of-right",
        output=Path("philosophy-of-right/philosophy-of-right.html"),
        converter=Path("philosophy-of-right/convert_book.py"),
        source_authority="PDF text layer",
        expected_figures=0,
        expected_note_refs=163,
        artifact_patterns=(
            r"This page intentionally",
            r"Great Clarendon",
            r"All rights reserved",
            r"ﬁ",
            r"ﬂ",
            r"Contents vi",
            r"(?<!over)scroll-behavior",
        ),
        special_checks=("publisher and metadata pages omitted",),
    ),
    ValidationCase(
        slug="the-lacanian-subject",
        output=Path("the-lacanian-subject/the-lacanian-subject.html"),
        converter=Path("the-lacanian-subject/convert_book.py"),
        source_authority="EPUB body, notes, index, and image fallbacks",
        expected_figures=73,
        expected_note_refs=246,
        artifact_patterns=(
            r"Copyright",
            r"All Rights Reserved",
            r"calibre",
            r"This book has been composed",
            r"Printed in the United",
            r"Wenran",
            r"Gédelian",
            r"NOTES TO",
            r"BIBLIOGRAPHY \d",
            r"INDEX \d",
            r"page-snapshot",
            r"ocr-images",
            r"transition_sb",
            r"<span class=\"epub\"><math",
            r"<mtext>Symbolic</mtext>",
            r"TILITIIII",
            r"LLddd",
            r"Baysy",
            r"©6\(",
        ),
        special_checks=(
            "MathML/image fallback decisions",
            "dashed separator opens navigator at any text size or viewport width",
            "no fallback note list expected",
        ),
    ),
)
