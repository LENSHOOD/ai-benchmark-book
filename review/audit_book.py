#!/usr/bin/env python3
"""Generate a deterministic structural and evidence-traceability inventory."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs" / "book"


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


sources = [
    json.loads(line)
    for line in (ROOT / "data" / "sources.jsonl").read_text().splitlines()
    if line.strip()
]
source_by_url = {normalize_url(row["raw_url"]): row for row in sources}
source_titles = Counter(row["title"].strip().lower() for row in sources)

chapters = []
all_book_urls: list[tuple[str, str]] = []
for path in sorted(BOOK.glob("*.md")):
    text = path.read_text()
    body = text.split("---", 2)[-1]
    urls = re.findall(r"https?://[^)\s>]+", body)
    all_book_urls.extend((path.name, url) for url in urls)
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", body)
        if p.strip() and not p.lstrip().startswith(("#", "- ", "```", ">", "|"))
    ]
    cited_paragraphs = [
        p for p in paragraphs if re.search(r"https?://|\[\d+\]", p)
    ]
    chapters.append(
        {
            "file": path.name,
            "chinese_chars": len(re.findall(r"[\u4e00-\u9fff]", body)),
            "h2": len(re.findall(r"^## ", body, flags=re.M)),
            "h3": len(re.findall(r"^### ", body, flags=re.M)),
            "paragraphs": len(paragraphs),
            "paragraphs_with_inline_citation": len(cited_paragraphs),
            "external_links": len(urls),
            "has_exercise": bool(re.search(r"练习|实践题|毕业项目", body)),
            "has_sources_section": bool(re.search(r"来源与延伸|延伸阅读", body)),
        }
    )

book_urls = {normalize_url(url) for _, url in all_book_urls}
unregistered_links = [
    {"chapter": chapter, "url": url}
    for chapter, url in all_book_urls
    if normalize_url(url) not in source_by_url
]

same_title_different_urls: dict[str, list[str]] = defaultdict(list)
for row in sources:
    same_title_different_urls[row["title"].strip().lower()].append(row["raw_url"])

payload = {
    "chapters": chapters,
    "totals": {
        "chapters": len(chapters),
        "chinese_chars": sum(row["chinese_chars"] for row in chapters),
        "paragraphs": sum(row["paragraphs"] for row in chapters),
        "paragraphs_with_inline_citation": sum(
            row["paragraphs_with_inline_citation"] for row in chapters
        ),
        "book_external_links": len(all_book_urls),
        "unique_book_external_links": len(book_urls),
        "registered_sources": len(sources),
        "sources_used_as_exact_book_links": sum(
            normalize_url(row["raw_url"]) in book_urls for row in sources
        ),
        "sources_with_unverified_metadata": sum(
            row.get("metadata_status") == "unverified" for row in sources
        ),
        "unregistered_book_links": len(unregistered_links),
    },
    "unregistered_book_links": unregistered_links,
    "duplicate_source_titles": {
        title: urls
        for title, urls in same_title_different_urls.items()
        if len(urls) > 1
    },
}

(ROOT / "review" / "content_inventory.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps(payload["totals"], ensure_ascii=False, indent=2))
