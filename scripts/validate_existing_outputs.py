from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from book_conversion_toolkit import validate_html
from conversion_cases import CASES


def main() -> int:
    failed = False
    for case in CASES:
        path = case.output_path(ROOT)
        if not path.exists():
            print(f"{path}: missing")
            failed = True
            continue
        report = validate_html(
            path,
            artifact_patterns=case.artifact_patterns,
            expected_note_refs=case.expected_note_refs,
            expected_figures=case.expected_figures,
            require_self_contained_images=True,
            require_standard_nav=case.require_standard_nav,
            reject_split_paragraphs=case.reject_split_paragraphs,
        )
        print(f"\n{path.relative_to(ROOT)}")
        print("\n".join(report.summary_lines()))
        failed = failed or not report.ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
