#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


RELEVANT_EXACT = {
    "AGENTS.md",
    "scripts/quality_gate.py",
    "scripts/validate_existing_outputs.py",
}


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    return Path(result.stdout.strip())


def changed_paths(root: Path) -> list[Path]:
    result = run(["git", "status", "--short", "--untracked-files=all"], root)
    paths: list[Path] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.rsplit(" -> ", 1)[1]
        paths.append(Path(raw_path))
    return paths


def is_relevant(path: Path) -> bool:
    text = path.as_posix()
    if text in RELEVANT_EXACT:
        return True
    if text.startswith("book_conversion_toolkit/"):
        return True
    if text.startswith("skills/book-conversion/"):
        return True
    if path.name == "convert_book.py":
        return True
    if path.suffix == ".html" and len(path.parts) == 2:
        return True
    return False


def cleanup(root: Path) -> None:
    shutil.rmtree(root / ".playwright-cli", ignore_errors=True)
    for pycache in root.rglob("__pycache__"):
        if ".git" not in pycache.parts:
            shutil.rmtree(pycache, ignore_errors=True)


def main() -> int:
    root = repo_root()
    cleanup(root)

    relevant = [path for path in changed_paths(root) if is_relevant(path)]
    if not relevant:
        print("Book conversion stop hook: no relevant converter/toolkit/HTML changes; skipped quality gate.", file=sys.stderr)
        return 0

    print("Book conversion stop hook: relevant changes detected; running quality gate.", file=sys.stderr)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        ["python3", "scripts/quality_gate.py"],
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout, file=sys.stderr, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        print("Book conversion stop hook: quality gate failed; fix the output before finishing.", file=sys.stderr)
        return result.returncode
    print("Book conversion stop hook: quality gate passed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

