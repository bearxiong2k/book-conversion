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
        ],
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
        )
        print(f"\n{path.relative_to(ROOT)}")
        print("\n".join(report.summary_lines()))
        failed = failed or not report.ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
