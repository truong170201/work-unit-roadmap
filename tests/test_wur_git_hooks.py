from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_REFERENCE = ROOT / "skills" / "wur-guidelines" / "references" / "git-hooks.md"


def extract_hook(reference: str, hook_name: str) -> str:
    pattern = rf"## `{re.escape(hook_name)}`.*?```sh\n(.*?)\n```"
    match = re.search(pattern, reference, flags=re.DOTALL)
    if not match:
        raise AssertionError(f"missing fenced sh block for {hook_name}")
    return match.group(1)


@unittest.skipUnless(shutil.which("git"), "git executable is required")
class WurGitHookEnforcementTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmpdir.name) / "repo"
        self.remote = Path(self.tmpdir.name) / "remote.git"
        self.repo.mkdir()
        self.reference = HOOK_REFERENCE.read_text(encoding="utf-8")
        self.git("init")
        self.git("checkout", "-b", "main")
        self.git("config", "user.email", "wur-test@example.invalid")
        self.git("config", "user.name", "WUR Test")
        self.install_hooks()
        self.write_all_md(active_phase="PHASE_1", active_wu="WU-P01-001")

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def run_cmd(
        self, *args: str, cwd: Path | None = None, check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            list(args),
            cwd=cwd or self.repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if check and result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        return result

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run_cmd("git", *args, check=check)

    def install_hooks(self) -> None:
        hooks = self.repo / ".githooks"
        hooks.mkdir()
        for name in ("commit-msg", "pre-commit", "pre-push"):
            path = hooks / name
            path.write_text(extract_hook(self.reference, name), encoding="utf-8")
        (hooks / ".wur-managed").write_text("", encoding="utf-8")
        self.git("config", "core.hooksPath", ".githooks")

    def write_all_md(self, *, active_phase: str, active_wu: str) -> None:
        path = self.repo / "agents" / "roadmap" / "ALL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"""
# Roadmap

## Current Status
- Default branch: main
- Active phase: {active_phase}
- Active Work Unit: {active_wu}
""".lstrip(),
            encoding="utf-8",
        )

    def stage_file(self, rel_path: str, text: str) -> None:
        path = self.repo / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.git("add", rel_path)

    def commit(
        self, message: str, *, allow_empty: bool = False
    ) -> subprocess.CompletedProcess[str]:
        args = ["commit", "-m", message]
        if allow_empty:
            args.insert(1, "--allow-empty")
        return self.git(*args, check=False)

    def assert_fails_with(
        self, result: subprocess.CompletedProcess[str], expected: str
    ) -> None:
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(expected, result.stdout + result.stderr)

    def create_remote(self) -> None:
        self.run_cmd(
            "git", "init", "--bare", str(self.remote), cwd=self.repo, check=True
        )
        self.git("remote", "add", "origin", str(self.remote))

    def test_commit_msg_accepts_only_wur_shapes(self) -> None:
        self.write_all_md(active_phase="none", active_wu="none")
        cases = {
            "bad message": False,
            "fix: update code": False,
            "WU-P01-003: add login validation": True,
            "WU-P01-003a: follow-up validation": True,
            "WU-P01-close: mark phase 1 done": True,
            "WU-P01-fix: merge fix/phase-1-empty-input": True,
            "WU-P01-abort: abandon phase 1": True,
            "WU-TW-001: bootstrap workspace": True,
            "Phase 1: merge feature/phase-1": True,
        }

        for message, should_pass in cases.items():
            with self.subTest(message=message):
                result = self.commit(message, allow_empty=True)
                self.assertEqual(
                    result.returncode == 0,
                    should_pass,
                    msg=result.stdout + result.stderr,
                )

    def test_pre_commit_blocks_implementation_on_default_branch(self) -> None:
        self.stage_file("src/app.py", "print('main')\n")

        result = self.commit("WU-P01-001: change implementation")

        self.assert_fails_with(
            result,
            "implementation changes cannot be committed from the default branch",
        )

    def test_pre_commit_requires_roadmap_update_with_implementation(self) -> None:
        self.git("checkout", "-b", "feature/phase-1")
        self.stage_file("src/app.py", "print('feature')\n")

        result = self.commit("WU-P01-001: change implementation")

        self.assert_fails_with(
            result,
            "implementation commits must stage agents/roadmap/ updates",
        )

    def test_pre_commit_allows_feature_phase_with_roadmap_trace(self) -> None:
        self.git("checkout", "-b", "feature/phase-1")
        self.stage_file("src/app.py", "print('feature')\n")
        self.stage_file("agents/roadmap/PHASE_1.md", "status: active\n")

        result = self.commit("WU-P01-001: change implementation")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_pre_commit_blocks_wrong_phase_branch(self) -> None:
        self.git("checkout", "-b", "feature/phase-2")
        self.stage_file("src/app.py", "print('wrong phase')\n")
        self.stage_file("agents/roadmap/PHASE_1.md", "status: active\n")

        result = self.commit("WU-P01-001: change implementation")

        self.assert_fails_with(
            result,
            "implementation changes must be committed from feature/phase-1",
        )

    def test_pre_push_blocks_default_branch_with_active_work(self) -> None:
        self.write_all_md(active_phase="PHASE_1", active_wu="none")
        all_md = self.repo / "agents" / "roadmap" / "ALL.md"
        self.stage_file("agents/roadmap/ALL.md", all_md.read_text(encoding="utf-8"))
        self.commit("WU-TW-001: record active roadmap")
        self.create_remote()

        result = self.git("push", "origin", "main", check=False)

        self.assert_fails_with(
            result, "cannot push default branch while Active phase is PHASE_1"
        )

    def test_pre_push_allows_default_branch_when_roadmap_idle(self) -> None:
        self.write_all_md(active_phase="none", active_wu="none")
        all_md = self.repo / "agents" / "roadmap" / "ALL.md"
        self.stage_file("agents/roadmap/ALL.md", all_md.read_text(encoding="utf-8"))
        self.commit("WU-TW-001: record idle roadmap")
        self.create_remote()

        result = self.git("push", "origin", "main", check=False)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_pre_push_allows_non_default_branch_with_active_work(self) -> None:
        self.write_all_md(active_phase="PHASE_1", active_wu="none")
        all_md = self.repo / "agents" / "roadmap" / "ALL.md"
        self.stage_file("agents/roadmap/ALL.md", all_md.read_text(encoding="utf-8"))
        self.commit("WU-TW-001: record active roadmap")
        self.git("checkout", "-b", "feature/phase-1")
        self.stage_file("agents/roadmap/PHASE_1.md", "status: active\n")
        self.commit("WU-TW-002: init phase metadata")
        self.create_remote()

        result = self.git("push", "origin", "feature/phase-1", check=False)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
