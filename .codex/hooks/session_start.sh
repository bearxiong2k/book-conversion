#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Book conversion hook guidance:
- Keep generated HTML reproducible from converter code; do not hand-edit final HTML.
- If converter, toolkit, validation script, or generated book HTML changes, regenerate as needed and run `PYTHONDONTWRITEBYTECODE=1 python3 scripts/quality_gate.py`.
- For CSS, navigation, formula, or figure changes, use a browser check in addition to the HTML quality gate.
EOF

