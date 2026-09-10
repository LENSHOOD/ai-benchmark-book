"""Negative regression tests for release gates."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from check_plain_language import find_violations
from source_manifest import ROOT, excluded_relative


class ReleaseGateTests(unittest.TestCase):
    def test_plain_language_gate_rejects_a_very_long_sentence(self):
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "probe.md"
            probe.write_text("这是一个故意写得很长的句子" * 20 + "。\n")
            self.assertTrue(find_violations(probe))

    def test_plain_language_gate_checks_lists_and_quotes(self):
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "probe.md"
            long_text = "这个列表项不应该因为使用了 Markdown 标记就绕过检查" * 15
            probe.write_text(f"- {long_text}。\n\n> {long_text}。\n")
            self.assertGreaterEqual(len(find_violations(probe)), 2)

    def test_plain_language_gate_joins_wrapped_lists_and_quotes(self):
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "probe.md"
            fragment = "手动换行不应该把同一个长句拆成几个短句"
            wrapped = "\n  ".join(fragment * 4 for _ in range(3))
            quoted = "\n> ".join(fragment * 4 for _ in range(3))
            probe.write_text(f"- {wrapped}。\n\n> {quoted}。\n")
            violations = find_violations(probe)
            sentence_violations = [item for item in violations if "sentence has" in item]
            self.assertEqual(len(sentence_violations), 2)

    def test_plain_language_gate_checks_tables_and_html_links(self):
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "probe.md"
            long_text = "这段说明不应该因为放在特殊格式里就绕过检查" * 15
            probe.write_text(f"| 名称 | {long_text} |\n\n<a href=\"/download\">下载</a>{long_text}。\n")
            self.assertGreaterEqual(len(find_violations(probe)), 2)

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

    def test_content_gate_rejects_a_missing_legacy_heading_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "book"
            for name in ("data", "docs", "examples", "scripts", "templates"):
                shutil.copytree(ROOT / name, fixture / name)
            chapter = fixture / "docs" / "book" / "10-skills.md"
            chapter.write_text(chapter.read_text().replace("skill-plugin-作为可验证干预", "wrong-anchor"))
            result = subprocess.run(
                [sys.executable, str(fixture / "scripts" / "check_book.py")],
                cwd=fixture,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("legacy heading anchor missing", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
