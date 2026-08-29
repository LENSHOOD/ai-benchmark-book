#!/usr/bin/env python3
"""Read-only health and schema audit for the downloadable Benchmark Radar."""

from __future__ import annotations

import csv
import json
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "benchmark_catalog.csv"
OUTPUT = ROOT / "review" / "catalog_audit.json"


def check_url(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 AI-Benchmark-Book-independent-review/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
            return {"url": url, "status": response.status, "final_url": response.url, "outcome": "reachable"}
    except urllib.error.HTTPError as error:
        outcome = "access_blocked" if error.code in {401, 403, 429} else "http_error"
        return {"url": url, "status": error.code, "final_url": error.url, "outcome": outcome}
    except Exception as error:  # audit output must retain exact transport failure
        return {"url": url, "status": None, "final_url": None, "outcome": "transport_error", "error": repr(error)}


with CATALOG.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))

urls = sorted({row["source"].strip() for row in rows if row.get("source", "").strip()})
with ThreadPoolExecutor(max_workers=12) as pool:
    health = list(pool.map(check_url, urls))

fields = list(rows[0].keys()) if rows else []
payload = {
    "row_count": len(rows),
    "fields": fields,
    "unique_values": {
        "maturity": sorted({row.get("maturity", "") for row in rows}),
        "openness": sorted({row.get("openness", "") for row in rows}),
    },
    "lifecycle_fields_present": sorted(set(fields) & {"status", "last_verified", "version", "revised_at", "retired_at"}),
    "url_summary": {
        outcome: sum(item["outcome"] == outcome for item in health)
        for outcome in sorted({item["outcome"] for item in health})
    },
    "url_health": health,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: payload[key] for key in ("row_count", "fields", "unique_values", "lifecycle_fields_present", "url_summary")}, ensure_ascii=False, indent=2))
