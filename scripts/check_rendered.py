#!/usr/bin/env python3
"""Check defects that can only be observed after VitePress rendering."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "docs" / ".vitepress" / "dist"


class LocalAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value and value.startswith("/"):
                self.urls.append(value)


parser = argparse.ArgumentParser()
parser.add_argument("--base", default="/", help="expected VitePress base path")
args = parser.parse_args()
expected_base = args.base if args.base.endswith("/") else f"{args.base}/"
statistics = DIST / "appendix" / "statistics.html"
if not statistics.exists():
    raise SystemExit("rendered statistics page is missing")
raw_markers = ("$$", "\\operatorname", "\\mathrm", "\\hat p", "\\frac{")
html_files = sorted(DIST.rglob("*.html"))
if not html_files:
    raise SystemExit("VitePress build produced no HTML pages")
raw_pages: dict[str, list[str]] = {}
wrong_base_paths: dict[str, list[str]] = {}
for path in html_files:
    html = path.read_text()
    found = [marker for marker in raw_markers if marker in html]
    if found:
        raw_pages[str(path.relative_to(DIST))] = found
    if expected_base != "/":
        asset_parser = LocalAssetParser()
        asset_parser.feed(html)
        wrong = sorted({url for url in asset_parser.urls if not url.startswith(expected_base)})
        if wrong:
            wrong_base_paths[str(path.relative_to(DIST))] = wrong[:10]
if raw_pages:
    raise SystemExit(f"raw TeX remains in rendered HTML: {raw_pages}")
if wrong_base_paths:
    raise SystemExit(f"rendered local URLs escape expected base {expected_base!r}: {wrong_base_paths}")
statistics_html = statistics.read_text()
if "mjx-container" not in statistics_html and "MathJax" not in statistics_html:
    raise SystemExit("rendered statistics page contains no MathJax output")
print(f"Rendered math/base-path gate passed across {len(html_files)} HTML pages (base={expected_base})")
