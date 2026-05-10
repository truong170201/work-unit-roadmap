from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "wur-guidelines" / "scripts" / "wur_codex_delegate.py"

spec = importlib.util.spec_from_file_location("wur_codex_delegate", SCRIPT)
assert spec is not None and spec.loader is not None
wur_codex_delegate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = wur_codex_delegate
spec.loader.exec_module(wur_codex_delegate)


class WurCodexDelegateTestCase(unittest.TestCase):
    def make_request(
        self,
        repo_root: Path,
        cwd: Path,
        *,
        allow_main: bool = False,
        read_only: bool = False,
        sandbox: str = "workspace-write",
        dry_run: bool = False,
    ):
        return wur_codex_delegate.DelegationRequest(
            repo_root=repo_root,
            cwd=cwd,
            role="reviewer",
            prompt="Review the scoped change.",
            phase="1",
            work_unit="WU-P1-001",
            model=None,
            effort=None,
            sandbox=sandbox,
            approval_policy="never",
            timeout_seconds=30,
            service_name="wur-codex-delegation",
            allow_main=allow_main,
            read_only=read_only,
            max_retries=0,
            dry_run=dry_run,
        )

    def test_scope_rejects_default_branch_without_explicit_allow_main(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            request = self.make_request(root, root)

            with self.assertRaisesRegex(
                wur_codex_delegate.DelegationError,
                "refusing Codex delegation on default branch",
            ):
                wur_codex_delegate.validate_scope(request)

    def test_read_only_request_requires_read_only_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            request = self.make_request(
                root,
                root,
                allow_main=True,
                read_only=True,
                sandbox="workspace-write",
            )

            with self.assertRaisesRegex(
                wur_codex_delegate.DelegationError,
                "read-only delegation requires --sandbox read-only",
            ):
                wur_codex_delegate.validate_scope(request)

    def test_allow_main_is_read_only_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            request = self.make_request(
                root,
                root,
                allow_main=True,
                read_only=False,
                sandbox="workspace-write",
            )

            with self.assertRaisesRegex(
                wur_codex_delegate.DelegationError,
                "--allow-main is only valid for read-only delegation",
            ):
                wur_codex_delegate.validate_scope(request)

    def test_thread_and_turn_requests_use_app_server_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / ".worktrees" / "phase-1"
            worktree.mkdir(parents=True)
            request = self.make_request(root, worktree)
            scope = {
                "cwd": str(worktree),
                "branch": "feature/phase-1",
                "default_branch": "main",
                "repo_root": str(root),
            }

            thread = wur_codex_delegate.build_thread_start_request(1, request, scope)
            turn = wur_codex_delegate.build_turn_start_request(
                2, "thr_test", request, scope
            )

            self.assertEqual(thread["jsonrpc"], "2.0")
            self.assertEqual(thread["method"], "thread/start")
            self.assertEqual(thread["params"]["threadSource"], "subagent")
            self.assertEqual(thread["params"]["sandbox"], "workspace-write")
            self.assertEqual(thread["params"]["serviceName"], "wur-codex-delegation")
            self.assertNotIn("mcp", json.dumps(thread).lower())

            self.assertEqual(turn["jsonrpc"], "2.0")
            self.assertEqual(turn["method"], "turn/start")
            self.assertEqual(turn["params"]["threadId"], "thr_test")
            self.assertIn("WU-P1-001", turn["params"]["input"][0]["text"])

            self.assertEqual(
                wur_codex_delegate.extract_thread_id({"id": "thr_direct"}),
                "thr_direct",
            )
            self.assertEqual(
                wur_codex_delegate.extract_thread_id({"thread": {"id": "thr_nested"}}),
                "thr_nested",
            )

    def test_rate_limit_classifier_catches_http_429_and_usage_limit(self) -> None:
        self.assertTrue(
            wur_codex_delegate.is_rate_limit_error(
                {
                    "message": "provider failed",
                    "codexErrorInfo": {
                        "responseStreamConnectionFailed": {"httpStatusCode": 429}
                    },
                }
            )
        )
        self.assertTrue(
            wur_codex_delegate.is_rate_limit_error(
                {"message": "limit", "codexErrorInfo": "usageLimitExceeded"}
            )
        )
        self.assertFalse(
            wur_codex_delegate.is_rate_limit_error(
                {"message": "syntax error", "codexErrorInfo": "badRequest"}
            )
        )

    def test_dry_run_writes_ledger_without_starting_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = root / "agents"
            agents.mkdir()
            worktree = root / ".worktrees" / "phase-1"
            worktree.mkdir(parents=True)
            request = self.make_request(root, worktree, dry_run=True)
            scope = {
                "cwd": str(worktree),
                "branch": "feature/phase-1",
                "default_branch": "main",
                "repo_root": str(root),
            }

            result = wur_codex_delegate.run_once(request, "codex", "codex-test", scope)

            self.assertEqual(result["status"], "dry-run")
            ledger = root / "agents" / "reports" / "codex-delegation" / "codex-test.json"
            self.assertTrue(ledger.exists())
            payload = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(payload["role"], "reviewer")
            self.assertEqual(payload["branch"], "feature/phase-1")

    def test_app_server_read_timeout_does_not_block_on_silent_process(self) -> None:
        command = [sys.executable, "-c", "import time; time.sleep(5)"]
        started = time.monotonic()
        with wur_codex_delegate.JsonlAppServerClient(
            command, ROOT, initialize=False
        ) as client:
            with self.assertRaises(TimeoutError):
                client.read_message(time.monotonic() + 0.2)
        self.assertLess(time.monotonic() - started, 2.0)


if __name__ == "__main__":
    unittest.main()
