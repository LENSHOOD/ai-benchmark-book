#!/usr/bin/env python3
"""Deterministic content, route, source, template and schema gates."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
import sys
import unicodedata
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT))

from examples.benchmark_core import load_tasks  # noqa: E402


def resolve_markdown_route(route: str, source: Path) -> Path | None:
    clean = route.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return source
    if clean == "/":
        return DOCS / "index.md"
    if clean.startswith("/"):
        candidate = DOCS / clean.lstrip("/")
    else:
        candidate = source.parent / clean
    options = (candidate, Path(f"{candidate}.md"), candidate / "index.md")
    return next((path for path in options if path.is_file() and path.suffix == ".md"), None)


def route_exists(route: str, source: Path) -> bool:
    clean = route.split("#", 1)[0].split("?", 1)[0]
    if resolve_markdown_route(route, source):
        return True
    if clean.startswith("/"):
        public_asset = DOCS / "public" / clean.lstrip("/")
    else:
        public_asset = DOCS / "public" / clean
    return public_asset.exists()


VITEPRESS_SPECIAL = set("~`!@#$%^&*()-_+=[]{}|\\;:\"'“”‘’<>,.?/")


def vitepress_slug(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    output: list[str] = []
    for character in normalized:
        if unicodedata.combining(character) or ord(character) < 32:
            continue
        output.append("-" if character.isspace() or character in VITEPRESS_SPECIAL else character)
    slug = re.sub(r"-{2,}", "-", "".join(output)).strip("-").lower()
    return f"_{slug}" if slug[:1].isdigit() else slug


def heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set(re.findall(r'<(?:a|span)\s+id="([^"]+)"', path.read_text()))
    counts: dict[str, int] = {}
    for match in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", path.read_text(), re.MULTILINE):
        title = match.group(1)
        title = re.sub(r"!?\[([^\]]+)\]\([^)]+\)", r"\1", title)
        title = re.sub(r"<[^>]+>", "", title)
        title = re.sub(r"[`*_~]", "", title)
        base = vitepress_slug(title)
        index = counts.get(base, 0)
        anchors.add(base if index == 0 else f"{base}-{index}")
        counts[base] = index + 1
    return anchors


def normalize_url(url: str) -> str:
    return url.split("#", 1)[0].rstrip("/")


errors: list[str] = []
markdown_files = sorted(
    path for path in DOCS.rglob("*.md")
    if not {"public", ".vitepress"}.intersection(path.relative_to(DOCS).parts)
)
chapters = sorted((DOCS / "book").glob("*.md"))
if len(chapters) != 16:
    errors.append(f"expected 16 chapters, found {len(chapters)}")

source_rows = [json.loads(line) for line in (ROOT / "data" / "sources.jsonl").read_text().splitlines() if line.strip()]
source_ids = [row["source_id"] for row in source_rows]
verified_primary_count = sum(row.get("metadata_status") == "verified_primary" for row in source_rows)
if len(source_rows) < 120:
    errors.append(f"source ledger unexpectedly shrank to {len(source_rows)} records")
if len(source_ids) != len(set(source_ids)):
    errors.append("duplicate source_id in source ledger")
registered_urls: set[str] = set()
for row in source_rows:
    for value in [row.get("raw_url"), row.get("canonical_locator"), *row.get("alternate_urls", [])]:
        if isinstance(value, str) and value.startswith("http"):
            registered_urls.add(normalize_url(value))
        elif isinstance(value, str) and value.startswith("arxiv:"):
            registered_urls.add(f"https://arxiv.org/abs/{value.split(':', 1)[1]}")

outbound_urls: set[str] = set()
for path in markdown_files:
    text = path.read_text()
    if any(marker in text for marker in ("TODO", "TBD", "PLACEHOLDER")):
        errors.append(f"placeholder in {path.relative_to(ROOT)}")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://")):
            outbound_urls.add(normalize_url(target))
            continue
        if target.startswith("mailto:"):
            continue
        if not route_exists(target, path):
            errors.append(f"broken internal route {target!r} in {path.relative_to(ROOT)}")
            continue
        if "#" in target:
            fragment = unquote(target.split("#", 1)[1].split("?", 1)[0])
            target_markdown = resolve_markdown_route(target, path)
            if fragment and target_markdown and fragment not in heading_anchors(target_markdown):
                errors.append(f"broken internal anchor #{fragment} in {target!r} from {path.relative_to(ROOT)}")

for url in sorted(outbound_urls - registered_urls):
    errors.append(f"unregistered outbound URL: {url}")

known_wrong = {
    "https://arxiv.org/abs/2604.01407": "SWE-Skills-Bench wrong paper",
    "https://arxiv.org/abs/2602.05395": "SupChain-Bench wrong paper",
    "https://arxiv.org/abs/2606.15862": "RetailBench superseded duplicate submission",
    "https://retailbench.github.io": "RetailBench dead project link",
}
all_markdown = "\n".join(path.read_text() for path in markdown_files)
for url, reason in known_wrong.items():
    if url in all_markdown:
        errors.append(f"known wrong link present ({reason}): {url}")

chapter_chars: dict[str, int] = {}
for path in chapters:
    chapter_text = path.read_text()
    count = len(re.findall(r"[\u4e00-\u9fff]", chapter_text))
    chapter_chars[path.name] = count
    if count < 1200:
        errors.append(f"chapter is too short to carry its stated teaching purpose: {path.name} ({count} CJK chars)")
    if "> **本章问题**" not in chapter_text:
        errors.append(f"chapter does not open with a decision question: {path.name}")

for name in ("commerce_supply_chain", "hardware_rnd"):
    task_path = ROOT / "examples" / name / "tasks.json"
    try:
        tasks = load_tasks(task_path)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid task schema in {name}: {exc}")
        continue
    if len(tasks) != 10:
        errors.append(f"{name} must match the ten scenarios in the chapter, found {len(tasks)}")

with (ROOT / "data" / "benchmark_catalog.csv").open(newline="") as handle:
    catalog = list(csv.DictReader(handle))
if len(catalog) < 70:
    errors.append(f"benchmark catalog unexpectedly shrank to {len(catalog)} records")
if {row["maturity"] for row in catalog} - {"foundational", "established", "evolving"}:
    errors.append("benchmark catalog maturity contains undocumented values")

mirror_pairs = [
    (ROOT / "data" / "sources.jsonl", DOCS / "public" / "downloads" / "sources.jsonl"),
    (ROOT / "data" / "benchmark_catalog.csv", DOCS / "public" / "downloads" / "benchmark_catalog.csv"),
]
for local in sorted((ROOT / "templates").iterdir()):
    if local.is_file():
        mirror_pairs.append((local, DOCS / "public" / "downloads" / "templates" / local.name))
for local, public in mirror_pairs:
    if not public.exists():
        errors.append(f"missing downloadable mirror: {public.relative_to(ROOT)}")
    elif local.read_bytes() != public.read_bytes():
        errors.append(f"download mirror drift: {local.relative_to(ROOT)} != {public.relative_to(ROOT)}")

config_text = (DOCS / ".vitepress" / "config.mts").read_text()
if "math: true" not in config_text:
    errors.append("VitePress math rendering is not enabled")
if "diagnostic_threshold: null" not in (ROOT / "templates" / "task_spec.yaml").read_text():
    errors.append("task template must not ship a context-free numeric threshold")

for label in ("来源事实", "综合判断", "实践建议", "未来推测"):
    if label not in all_markdown:
        errors.append(f"evidence voice is documented but never used: {label}")

public_process_phrases = ("用户最初提供", "验证码阻断")
for phrase in public_process_phrases:
    if phrase in all_markdown:
        errors.append(f"public documentation leaks an internal collection detail: {phrase}")

framework_hosts = {
    "02-history.md": "综合判断",
    "03-language.md": "实践建议",
    "10-skills.md": "来源事实",
    "12-enterprise-fde.md": "实践建议",
    "13-commerce-supply-chain.md": "来源事实",
    "14-hardware-rnd.md": "来源事实",
    "15-governance.md": "实践建议",
    "16-future.md": "实践建议",
}
for filename, label in framework_hosts.items():
    if label not in (DOCS / "book" / filename).read_text():
        errors.append(f"chapter with an original framework or empirical anchor lacks {label}: {filename}")

framework_inlinks = sum("/appendix/framework-map" in path.read_text() for path in chapters)
if framework_inlinks < 10:
    errors.append(f"framework map is insufficiently connected to host chapters: {framework_inlinks}/10")

legacy_heading_anchors = {
    "09-harness.md": '<a id="harness-被忽略的系统变量"></a>',
    "10-skills.md": '<a id="skill-plugin-作为可验证干预"></a>',
    "11-experiments.md": '<a id="实验设计、统计与因果归因"></a>',
    "15-governance.md": '<a id="上岗、授权、复证与-benchmark-治理"></a>',
    "16-future.md": '<a id="评测评测本身-以及未来"></a>',
}
for filename, anchor in legacy_heading_anchors.items():
    if anchor not in (DOCS / "book" / filename).read_text():
        errors.append(f"legacy heading anchor missing from {filename}: {anchor}")

empirical_anchors = {
    "08-agents.md": "https://arxiv.org/abs/2601.11868",
    "09-harness.md": "https://arxiv.org/abs/2602.12670",
    "13-commerce-supply-chain.md": "https://arxiv.org/abs/2607.28956",
    "14-hardware-rnd.md": "https://arxiv.org/abs/2604.01532",
}
for filename, url in empirical_anchors.items():
    if url not in (DOCS / "book" / filename).read_text():
        errors.append(f"verified empirical anchor missing from {filename}: {url}")

home_text = (DOCS / "index.md").read_text()
if "v0.5 beta" not in home_text:
    errors.append("home page must disclose the current beta maturity")
if not re.search(rf"共(?:有)? {verified_primary_count} 条标记为 `verified_primary`", home_text):
    errors.append("home page verified-source count does not match the source ledger")

reference_count = len(re.findall(r"^\*\*\[\d+\]\*\*", (DOCS / "appendix" / "references.md").read_text(), re.MULTILINE))
if reference_count != len(source_rows):
    errors.append(f"generated references ({reference_count}) do not match source ledger ({len(source_rows)})")

chinese_chars = sum(chapter_chars.values())
print(json.dumps({
    "markdown_files": len(markdown_files),
    "chapters": len(chapters),
    "chapter_chinese_chars": chinese_chars,
    "benchmark_records": len(catalog),
    "sources": len(source_rows),
    "registered_outbound_urls": len(outbound_urls),
    "errors": errors,
}, ensure_ascii=False, indent=2))
if errors:
    raise SystemExit(1)
