#!/usr/bin/env python3
"""Build or verify a deterministic manifest for release source files."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release" / "v0.4.0-source.sha256"
ROOT_FILES = {
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE-CODE",
    "LICENSE-CONTENT",
    "README.md",
    "package-lock.json",
    "package.json",
}
SOURCE_DIRS = {".github", "data", "docs", "examples", "scripts", "templates"}


def excluded_relative(relative: Path) -> bool:
    """Return whether a repository-relative source path is a generated artifact."""

    if relative.as_posix() == MANIFEST.relative_to(ROOT).as_posix():
        return True
    if relative.name == ".DS_Store" or {"__pycache__", ".pytest_cache"}.intersection(relative.parts):
        return True
    if relative.parts[:2] == ("docs", ".vitepress") and {"dist", "cache"}.intersection(relative.parts):
        return True
    return relative.parts[:1] == ("examples",) and "results" in relative.parts[1:]


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if not path.is_file():
        return False
    if excluded_relative(relative):
        return False
    return relative.as_posix() in ROOT_FILES or relative.parts[0] in SOURCE_DIRS


def render() -> str:
    paths = sorted((path for path in ROOT.rglob("*") if included(path)), key=lambda path: path.relative_to(ROOT).as_posix())
    return "".join(f"{sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}\n" for path in paths)


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = render()
    if args.write:
        MANIFEST.parent.mkdir(exist_ok=True)
        MANIFEST.write_text(current)
        print(f"Wrote {len(current.splitlines())} source hashes to {MANIFEST}")
        return
    if not MANIFEST.exists():
        raise SystemExit(f"source manifest is missing: {MANIFEST}")
    if MANIFEST.read_text() != current:
        raise SystemExit("release source manifest is stale; review changes and regenerate it explicitly")
    print(f"Source manifest verified ({len(current.splitlines())} files)")


if __name__ == "__main__":
    main()
