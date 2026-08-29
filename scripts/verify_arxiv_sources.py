#!/usr/bin/env python3
"""Verify and optionally refresh arXiv ledger metadata from the primary API.

This is a networked maintenance command, deliberately separate from the
offline release gate. It updates only metadata fields; source identity and
book claims still require editorial review.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "sources.jsonl"
MIRROR = ROOT / "docs" / "public" / "downloads" / "sources.jsonl"
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def arxiv_id(row: dict) -> str | None:
    locator = str(row.get("canonical_locator", ""))
    if locator.startswith("arxiv:"):
        return re.sub(r"v\d+$", "", locator.split(":", 1)[1])
    match = re.search(r"arxiv\.org/abs/([^?#]+)", str(row.get("raw_url", "")))
    return re.sub(r"v\d+$", "", match.group(1).rstrip("/")) if match else None


def compact(text: str | None) -> str:
    return " ".join((text or "").split())


def fetch(ids: list[str], timeout: float, batch_size: int = 20) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for offset in range(0, len(ids), batch_size):
        batch = ids[offset:offset + batch_size]
        url = "https://export.arxiv.org/api/query?" + urlencode({"id_list": ",".join(batch), "max_results": len(batch)})
        request = Request(url, headers={"User-Agent": "AI-Benchmark-Book-Arxiv-Audit/0.3 (metadata verification)"})
        with urlopen(request, timeout=timeout) as response:
            root = ElementTree.fromstring(response.read())
        for entry in root.findall("a:entry", ATOM):
            entry_url = compact(entry.findtext("a:id", default="", namespaces=ATOM))
            match = re.search(r"/abs/([^?#]+)", entry_url)
            if not match:
                continue
            versioned = match.group(1).rstrip("/")
            base_id = re.sub(r"v\d+$", "", versioned)
            version_match = re.search(r"v(\d+)$", versioned)
            authors = [compact(node.findtext("a:name", default="", namespaces=ATOM)) for node in entry.findall("a:author", ATOM)]
            author_text = "; ".join(authors) if len(authors) <= 4 else f"{authors[0]} et al."
            published = compact(entry.findtext("a:published", default="", namespaces=ATOM))
            found[base_id] = {
                "title": compact(entry.findtext("a:title", default="", namespaces=ATOM)),
                "authors": author_text,
                "year": published[:4],
                "version": f"v{version_match.group(1)}" if version_match else "v1",
            }
        if offset + batch_size < len(ids):
            time.sleep(3)
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write verified metadata to the source ledger and public mirror")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    rows = [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]
    indexed = [(row, arxiv_id(row)) for row in rows]
    ids = sorted({identifier for _, identifier in indexed if identifier})
    metadata = fetch(ids, args.timeout)
    missing = sorted(set(ids) - set(metadata))
    if missing:
        raise SystemExit(f"arXiv API returned no entry for: {missing}")

    changed = 0
    for row, identifier in indexed:
        if not identifier:
            continue
        authoritative = metadata[identifier]
        updates = {
            **authoritative,
            "metadata_status": "verified_primary",
            "accessed_on": date.today().isoformat(),
        }
        if any(row.get(key) != value for key, value in updates.items()):
            changed += 1
        row.update(updates)

    if args.write:
        rendered = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
        LEDGER.write_text(rendered)
        MIRROR.write_text(rendered)

    print(json.dumps({
        "arxiv_records": len(ids),
        "api_matches": len(metadata),
        "records_changed": changed,
        "written": args.write,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
