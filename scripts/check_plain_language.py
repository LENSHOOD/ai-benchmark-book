#!/usr/bin/env python3
"""Reject reader-facing prose that has drifted back into very long sentences."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXCLUDED = {
    DOCS / "appendix" / "references.md",
    DOCS / "changelog.md",
}
MAX_SENTENCE_CHARS = 180
MAX_PARAGRAPH_CHARS = 360


def reader_files() -> list[Path]:
    return sorted(
        path
        for path in DOCS.rglob("*.md")
        if path not in EXCLUDED and "public" not in path.parts and ".vitepress" not in path.parts
    )


def visible_text(text: str) -> str:
    text = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<https?://[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"</?[^>]+>", "", text)
    text = re.sub(r"[`*_>#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def prose_paragraphs(path: Path) -> list[tuple[int, str]]:
    paragraphs: list[tuple[int, str]] = []
    buffer: list[str] = []
    buffer_kind = "prose"
    start = 0
    in_frontmatter = False
    in_fence = False

    def flush() -> None:
        nonlocal buffer, buffer_kind
        if buffer:
            paragraphs.append((start, visible_text(" ".join(buffer))))
            buffer = []
            buffer_kind = "prose"

    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if number == 1 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue
        if line.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line:
            flush()
            continue
        if line.startswith(("#", "$$", ":::", "<script", "</script")):
            flush()
            continue
        if line.startswith("|"):
            flush()
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            for cell in cells:
                if cell and not re.fullmatch(r":?-{3,}:?", cell):
                    paragraphs.append((number, visible_text(cell)))
            continue
        list_item = re.match(r"^(?:[-*+]|\d+[.)])\s+(.*)", line)
        if list_item:
            flush()
            start = number
            buffer_kind = "list"
            buffer.append(list_item.group(1))
            continue
        if line.startswith(">"):
            if buffer_kind != "quote":
                flush()
                start = number
                buffer_kind = "quote"
            buffer.append(re.sub(r"^>+\s*", "", line))
            continue
        if not buffer:
            start = number
        buffer.append(line)
    flush()
    return paragraphs


def find_violations(path: Path) -> list[str]:
    violations: list[str] = []
    for line, paragraph in prose_paragraphs(path):
        if len(paragraph) > MAX_PARAGRAPH_CHARS:
            violations.append(f"{path}:{line}: paragraph has {len(paragraph)} visible chars")
        for sentence in re.split(r"[。！？!?；;]", paragraph):
            sentence = sentence.strip()
            if len(sentence) > MAX_SENTENCE_CHARS:
                violations.append(f"{path}:{line}: sentence has {len(sentence)} visible chars")
    return violations


def main() -> None:
    violations = [item for path in reader_files() for item in find_violations(path)]
    if violations:
        print("Plain-language gate failed:")
        print("\n".join(f"- {item}" for item in violations))
        raise SystemExit(1)
    print(
        f"Plain-language gate passed ({len(reader_files())} reader-facing files, "
        f"sentence <= {MAX_SENTENCE_CHARS}, paragraph <= {MAX_PARAGRAPH_CHARS})"
    )


if __name__ == "__main__":
    main()
