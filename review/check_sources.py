#!/usr/bin/env python3
"""Risk-screen source URLs without mutating the canonical source ledger."""

from __future__ import annotations

import json
import re
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ROWS = [
    json.loads(line)
    for line in (ROOT / "data" / "sources.jsonl").read_text().splitlines()
    if line.strip()
]
SSL_CONTEXT = ssl.create_default_context()


def check(row: dict) -> dict:
    request = Request(
        row["raw_url"],
        headers={
            "User-Agent": "Mozilla/5.0 AI-Benchmark-Book-Source-Audit/0.1",
            "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
        },
    )
    result = {
        "source_id": row["source_id"],
        "expected_title": row["title"],
        "url": row["raw_url"],
        "status": None,
        "final_url": None,
        "content_type": None,
        "page_title": None,
        "classification": None,
        "error": None,
    }
    try:
        with urlopen(request, timeout=12, context=SSL_CONTEXT) as response:
            result["status"] = response.status
            result["final_url"] = response.geturl()
            result["content_type"] = response.headers.get("Content-Type", "")
            body = response.read(350_000)
            if "html" in result["content_type"].lower():
                decoded = body.decode("utf-8", errors="ignore")
                match = re.search(r"<title[^>]*>(.*?)</title>", decoded, flags=re.I | re.S)
                if match:
                    result["page_title"] = re.sub(r"\s+", " ", match.group(1)).strip()
            result["classification"] = "reachable"
    except HTTPError as exc:
        result["status"] = exc.code
        result["final_url"] = exc.geturl()
        result["error"] = str(exc)
        result["classification"] = (
            "access_blocked" if exc.code in {401, 403, 406, 409, 418, 429, 451} else "http_error"
        )
    except (URLError, TimeoutError, OSError) as exc:
        result["error"] = str(exc)
        text = str(exc).lower()
        result["classification"] = "timeout" if "timed out" in text else "network_error"
    return result


with ThreadPoolExecutor(max_workers=12) as pool:
    futures = [pool.submit(check, row) for row in ROWS]
    results = [future.result() for future in as_completed(futures)]

results.sort(key=lambda row: row["source_id"])
summary: dict[str, int] = {}
for row in results:
    summary[row["classification"]] = summary.get(row["classification"], 0) + 1

payload = {"checked": len(results), "summary": summary, "results": results}
(ROOT / "review" / "source_health.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps({"checked": len(results), "summary": summary}, ensure_ascii=False, indent=2))
