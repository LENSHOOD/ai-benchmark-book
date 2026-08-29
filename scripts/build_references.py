#!/usr/bin/env python3
"""Generate a readable VitePress bibliography from the registered source ledger."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.jsonl"
OUTPUT = ROOT / "docs" / "appendix" / "references.md"


def publisher(url: str) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    return host or "原始来源"


rows = [json.loads(line) for line in SOURCES.read_text().splitlines() if line.strip()]
content = [
    "---",
    "title: 参考文献",
    "description: 本书的论文、官方项目、代码、标准与研究机构来源",
    "---",
    "",
    "# 参考文献",
    "",
    "以下来源继承自研究证据账本，注册与复核日期为 2026-08-22 至 2026-08-28。`verified_primary` 表示本版已回到一手页面核对核心元数据；`unverified` 表示仅注册、尚未完成逐条元数据审定。来源类型用于导航，不代表单篇材料自动可信。",
    "",
]
for index, row in enumerate(rows, 1):
    url = row.get("raw_url") or row["canonical_locator"]
    title = row.get("title") or "未命名来源"
    year = row.get("year") or "n.d."
    source_type = row.get("source_type") or "source"
    author = (row.get("authors") or publisher(url)).rstrip(".")
    content.extend(
        [
            f'<span id="ref-{index}"></span>',
            f"**[{index}]** {author}. ({year}). [{title}]({url}). *{source_type}.*",
            "",
        ]
    )
OUTPUT.write_text("\n".join(content))
print(f"Wrote {len(rows)} references to {OUTPUT}")
