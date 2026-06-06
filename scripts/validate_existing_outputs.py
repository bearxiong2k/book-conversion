from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from book_conversion_toolkit import validate_html


CASES = [
    {
        "path": ROOT / "clinical-intro/a-clinical-introduction-to-lacanian-psychoanalysis.html",
        "figures": 30,
        "scan": [
            r"Chapter are",
            r"run-of-themill",
            r"dtfense",
            r"jonissance",
            r"DSM-Ill",
        ],
        "require_standard_nav": True,
    },
    {
        "path": ROOT / "enjoy-your-symptom/enjoy-your-symptom.html",
        "figures": 8,
        "notes": 263,
        "scan": [
            r"replusive",
            r"Englightenment",
            r"Idealogy",
            r"Kierkegaard's materialist r<",
        ],
        "require_standard_nav": True,
        "reject_split_paragraphs": True,
    },
    {
        "path": ROOT / "the-idea-of-phenomenology/the-idea-of-phenomenology.html",
        "notes": 11,
        "scan": [
            r"AAO",
            r"pet&amp;",
            r"natiirliche",
            r"Jiirgen",
            r"Phanomen",
        ],
        "require_standard_nav": True,
    },
    {
        "path": ROOT / "sublime-object-of-ideaology/the-sublime-object-frontmatter.html",
        "figures": 5,
        "scan": [
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
        ],
        "require_standard_nav": True,
    },
    {
        "path": ROOT / "for-they-know-not/for-they-know-not.html",
        "figures": 11,
        "notes": 371,
        "scan": [
            r"Roudedge",
            r"direcdy",
            r"detaded",
            r"forgetten",
            r"mouuement",
            r"silendy",
            r"Weatherhilt",
            r"suiprising",
            r"(?<!over)scroll-behavior",
        ],
        "require_standard_nav": True,
    },
    {
        "path": ROOT / "how-to-read/how-to-read-lacan.html",
        "figures": 0,
        "notes": 60,
        "scan": [
            r"calibre",
            r"filepos",
            r"How to Read Lacan How to Read Lacan",
            r"(?<!over)scroll-behavior",
            r"\bamella\b",
            r"llamella",
            r"dano ferentes",
        ],
        "require_standard_nav": True,
    },
    {
        "path": ROOT / "philosophy-of-right/philosophy-of-right.html",
        "notes": 163,
        "figures": 0,
        "scan": [
            r"This page intentionally",
            r"Great Clarendon",
            r"All rights reserved",
            r"ﬁ",
            r"ﬂ",
            r"Contents vi",
            r"(?<!over)scroll-behavior",
        ],
        "require_standard_nav": True,
    },
    {
        "path": ROOT / "the-lacanian-subject/the-lacanian-subject.html",
        "figures": 73,
        "notes": 246,
        "scan": [
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
            r"TILITIIII",
            r"LLddd",
            r"Baysy",
            r"©6\(",
        ],
        "require_standard_nav": True,
    },
]


def main() -> int:
    failed = False
    for case in CASES:
        path = case["path"]
        if not path.exists():
            print(f"{path}: missing")
            failed = True
            continue
        report = validate_html(
            path,
            artifact_patterns=case.get("scan", []),
            expected_note_refs=case.get("notes"),
            expected_figures=case.get("figures"),
            require_standard_nav=case.get("require_standard_nav", False),
            reject_split_paragraphs=case.get("reject_split_paragraphs", False),
        )
        print(f"\n{path.relative_to(ROOT)}")
        print("\n".join(report.summary_lines()))
        failed = failed or not report.ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
