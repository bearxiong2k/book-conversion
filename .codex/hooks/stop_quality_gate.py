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


def staged_paths(root: Path) -> list[Path]:
    result = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"], root)
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def unstaged_paths(root: Path) -> list[Path]:
    result = run(["git", "diff", "--name-only", "--diff-filter=ACMRT"], root)
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


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


def run_quality_gate(root: Path, label: str) -> int:
    print(f"Book conversion {label}: relevant changes detected; running quality gate.", file=sys.stderr)
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
        print(f"Book conversion {label}: quality gate failed; fix the output before finishing.", file=sys.stderr)
        return result.returncode
    print(f"Book conversion {label}: quality gate passed.", file=sys.stderr)
    return 0


def pre_commit(root: Path) -> int:
    relevant_staged = [path for path in staged_paths(root) if is_relevant(path)]
    if not relevant_staged:
        print("Book conversion pre-commit hook: no relevant staged changes; skipped quality gate.", file=sys.stderr)
        return 0

    relevant_unstaged = [path for path in unstaged_paths(root) if is_relevant(path)]
    if relevant_unstaged:
        print("Book conversion pre-commit hook: relevant unstaged changes remain:", file=sys.stderr)
        for path in relevant_unstaged:
            print(f"  - {path.as_posix()}", file=sys.stderr)
        print("Stage or revert these before committing so converter/output changes stay together.", file=sys.stderr)
        return 1

    return run_quality_gate(root, "pre-commit hook")


def main() -> int:
    root = repo_root()
    cleanup(root)

    if "--staged" in sys.argv[1:]:
        return pre_commit(root)

    relevant = [path for path in changed_paths(root) if is_relevant(path)]
    if not relevant:
        print("Book conversion stop hook: no relevant converter/toolkit/HTML changes; skipped quality gate.", file=sys.stderr)
        return 0

    return run_quality_gate(root, "stop hook")


if __name__ == "__main__":
    raise SystemExit(main())
