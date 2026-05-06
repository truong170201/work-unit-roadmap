from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "skills" / "wur-guidelines" / "scripts" / "wur_meta_consistency.py"


class WurMetaConsistencyTestCase(unittest.TestCase):
    def test_meta_consistency_checker_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(ROOT)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("[OK]", result.stdout)

    def test_meta_consistency_checker_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(ROOT), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["findings"], [])

    def test_meta_consistency_checker_fails_on_missing_root(self) -> None:
        missing = ROOT / "DOES_NOT_EXIST"
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(missing)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("target root does not exist", result.stdout)


if __name__ == "__main__":
    unittest.main()
