from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.benchmark_core import compare, summarize, write_results
from examples.commerce_supply_chain.run import run as run_commerce
from examples.hardware_rnd.run import run as run_hardware


OUTPUT_ROOT = Path(__file__).resolve().parent / "results"
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

for name, runner in (("commerce_supply_chain", run_commerce), ("hardware_rnd", run_hardware)):
    rows = runner()
    run_dir = write_results(OUTPUT_ROOT, rows, f"{stamp}-{name}")
    payload = {
        "suite": name,
        "result_directory": str(run_dir),
        "summary": summarize(rows),
        "paired_comparison": compare(rows, "basic.direct.none", "capable.workflow.domain"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
