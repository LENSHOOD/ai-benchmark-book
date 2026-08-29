"""Negative regression tests for release gates."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from source_manifest import ROOT, excluded_relative


class ReleaseGateTests(unittest.TestCase):
    def test_source_manifest_excludes_nested_result_artifacts(self):
        nested_result = Path("examples/commerce_supply_chain/results/run/trials.jsonl")
        self.assertTrue(excluded_relative(nested_result))

    def test_source_manifest_excludes_ignored_local_caches(self):
        ignored = (
            Path("docs/.vitepress/cache/deps.json"),
            Path("docs/.vitepress/dist/index.html"),
            Path("examples/commerce_supply_chain/.pytest_cache/state"),
            Path("examples/__pycache__/benchmark_core.pyc"),
        )
        for path in ignored:
            with self.subTest(path=path):
                self.assertTrue(excluded_relative(path))

    def test_content_gate_rejects_a_broken_internal_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "book"
            for name in ("data", "docs", "examples", "scripts", "templates"):
                shutil.copytree(ROOT / name, fixture / name)
            index = fixture / "docs" / "index.md"
            index.write_text(index.read_text() + "\n[negative gate probe](/book/01-why-eval#missing-anchor-probe)\n")
            result = subprocess.run(
                [sys.executable, str(fixture / "scripts" / "check_book.py")],
                cwd=fixture,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("broken internal anchor", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
