#!/usr/bin/env python3
"""Validate the source ledger; optionally probe URLs without treating 403 as dead."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--online", action="store_true", help="probe registered URLs; intended for scheduled maintenance")
parser.add_argument("--timeout", type=float, default=8.0)
args = parser.parse_args()

rows = [json.loads(line) for line in (ROOT / "data" / "sources.jsonl").read_text().splitlines() if line.strip()]
errors: list[str] = []
allowed_status = {"unverified", "verified_primary"}
for row in rows:
    source_id = row.get("source_id", "<missing>")
    for key in ("source_id", "canonical_locator", "raw_url", "title", "source_type", "metadata_status"):
        if not row.get(key):
            errors.append(f"{source_id}: missing {key}")
    if row.get("metadata_status") not in allowed_status:
        errors.append(f"{source_id}: unknown metadata_status {row.get('metadata_status')!r}")
    if row.get("metadata_status") == "verified_primary":
        for key in ("authors", "year", "accessed_on"):
            if not row.get(key):
                errors.append(f"{source_id}: verified_primary requires {key}")

ids = [row.get("source_id") for row in rows]
if len(ids) != len(set(ids)):
    errors.append("duplicate source_id")

health: dict[str, int] = {}
if args.online:
    def arxiv_id(row: dict) -> str | None:
        locator = str(row.get("canonical_locator", ""))
        if locator.startswith("arxiv:"):
            return re.sub(r"v\d+$", "", locator.split(":", 1)[1])
        match = re.search(r"arxiv\.org/abs/([^?#]+)", str(row.get("raw_url", "")))
        return re.sub(r"v\d+$", "", match.group(1).rstrip("/")) if match else None

    def normalized_title(value: str) -> str:
        value = unicodedata.normalize("NFKC", value).casefold()
        return "".join(character for character in value if character.isalnum())

    arxiv_rows = {identifier: row for row in rows if (identifier := arxiv_id(row))}
    arxiv_titles: dict[str, str] = {}
    arxiv_ids = sorted(arxiv_rows)
    atom = {"a": "http://www.w3.org/2005/Atom"}
    for offset in range(0, len(arxiv_ids), 20):
        batch = arxiv_ids[offset:offset + 20]
        url = "https://export.arxiv.org/api/query?" + urlencode({"id_list": ",".join(batch), "max_results": len(batch)})
        request = Request(url, headers={"User-Agent": "AI-Benchmark-Book-Source-Audit/0.3"})
        try:
            with urlopen(request, timeout=max(args.timeout, 15.0)) as response:
                feed = ElementTree.fromstring(response.read())
            for entry in feed.findall("a:entry", atom):
                entry_url = "".join(entry.findtext("a:id", default="", namespaces=atom).split())
                match = re.search(r"/abs/([^?#]+)", entry_url)
                if match:
                    identifier = re.sub(r"v\d+$", "", match.group(1).rstrip("/"))
                    arxiv_titles[identifier] = " ".join(entry.findtext("a:title", default="", namespaces=atom).split())
        except (HTTPError, URLError, TimeoutError, ElementTree.ParseError) as exc:
            errors.append(f"arXiv title audit failed for batch {batch[0]}..: {type(exc).__name__}")

    for identifier, row in arxiv_rows.items():
        if identifier not in arxiv_titles:
            errors.append(f"{row['source_id']}: arXiv id not returned by primary API: {identifier}")
        elif normalized_title(row["title"]) != normalized_title(arxiv_titles[identifier]):
            errors.append(f"{row['source_id']}: arXiv title mismatch for {identifier}: {row['title']!r} != {arxiv_titles[identifier]!r}")
        else:
            health["arxiv_title_match"] = health.get("arxiv_title_match", 0) + 1

    def probe(row: dict) -> tuple[str, str]:
        url = row["raw_url"]
        request = Request(url, headers={"User-Agent": "AI-Benchmark-Book-Source-Audit/0.3"})
        try:
            with urlopen(request, timeout=args.timeout) as response:
                return row["source_id"], f"ok:{response.status}"
        except HTTPError as exc:
            if exc.code in {401, 403, 429}:
                return row["source_id"], f"access_control:{exc.code}"
            if exc.code in {404, 410}:
                return row["source_id"], f"dead:{exc.code}"
            return row["source_id"], f"http_error:{exc.code}"
        except (URLError, TimeoutError) as exc:
            return row["source_id"], f"network_error:{type(exc).__name__}"

    with ThreadPoolExecutor(max_workers=8) as pool:
        for source_id, status in pool.map(probe, rows):
            category = status.split(":", 1)[0]
            health[category] = health.get(category, 0) + 1
            if category == "dead":
                errors.append(f"{source_id}: {status}")

print(json.dumps({"records": len(rows), "verified_primary": sum(r["metadata_status"] == "verified_primary" for r in rows), "health": health, "errors": errors}, ensure_ascii=False, indent=2))
if errors:
    raise SystemExit(1)
