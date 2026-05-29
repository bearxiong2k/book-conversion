#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS="${ROOT}/.codex_deps"

python3 -m pip install --upgrade --target "${DEPS}" -r "${ROOT}/requirements.txt"

cat <<MSG
Installed Python dependencies into ${DEPS}.
Use this import path in conversion scripts when needed:

  import sys
  sys.path.insert(0, "../.codex_deps")
  sys.path.insert(0, "..")

For OCR conversions, install the system tesseract binary separately if it is not already available.
MSG
