from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginManifestTestCase(unittest.TestCase):
    def read_json(self, relative_path: str) -> dict:
        path = ROOT / relative_path
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_repo_bundles_only_claude_plugin_manifest(self) -> None:
        self.assertFalse((ROOT / ".codex-plugin" / "plugin.json").exists())
        self.assertTrue((ROOT / ".claude-plugin" / "plugin.json").exists())

    def test_readme_documents_claude_as_the_only_bundled_plugin(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("a Claude Code Plugin", readme)
        self.assertIn("Other platforms", readme)
        self.assertIn("not bundled as first-class plugin targets", readme)
        self.assertNotIn("codex plugin marketplace add", readme)
        self.assertNotIn(".codex-plugin/plugin.json", readme)

    def test_claude_manifest_remains_namespaced_as_wur(self) -> None:
        manifest = self.read_json(".claude-plugin/plugin.json")

        self.assertEqual(manifest["name"], "wur")
        self.assertEqual(manifest["version"], "2.0.0")

    def test_command_docs_exist_for_claude_plugin(self) -> None:
        command_files = [
            "init.md",
            "upgrade.md",
            "start.md",
            "test.md",
            "done.md",
            "abort.md",
            "status.md",
            "wiki/upgrade.md",
            "wiki/add.md",
            "wiki/ask.md",
            "wiki/lint.md",
            "wiki/stats.md",
            "wiki/graph.md",
        ]

        for command_file in command_files:
            with self.subTest(command_file=command_file):
                self.assertTrue((ROOT / "commands" / command_file).exists())


if __name__ == "__main__":
    unittest.main()
