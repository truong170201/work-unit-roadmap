#!/usr/bin/env python3
"""Optional Codex App Server delegation helper for WUR.

This script is intentionally small and defensive. It starts its own
`codex app-server` subprocess, creates one thread in the requested worktree,
starts one turn, records a ledger entry, unsubscribes only that thread, and
then terminates only the subprocess it started.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import random
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_SERVER_METHOD_THREAD_START = "thread/start"
APP_SERVER_METHOD_TURN_START = "turn/start"
APP_SERVER_METHOD_TURN_INTERRUPT = "turn/interrupt"
APP_SERVER_METHOD_THREAD_UNSUBSCRIBE = "thread/unsubscribe"
APP_SERVER_TURN_COMPLETED = "turn/completed"
APP_SERVER_METHOD_INITIALIZE = "initialize"

RATE_LIMIT_CODES = {
    429,
}

RATE_LIMIT_KINDS = {
    "usageLimitExceeded",
    "serverOverloaded",
}


class DelegationError(RuntimeError):
    """Raised for expected delegation failures."""


class AppServerRequestError(DelegationError):
    """Raised when App Server returns a JSON-RPC error object."""

    def __init__(self, error: dict[str, Any]) -> None:
        super().__init__(json.dumps(error, sort_keys=True))
        self.error = error


@dataclass(frozen=True)
class DelegationRequest:
    repo_root: Path
    cwd: Path
    role: str
    prompt: str
    phase: str | None
    work_unit: str | None
    model: str | None
    effort: str | None
    sandbox: str
    approval_policy: str
    timeout_seconds: int
    service_name: str
    allow_main: bool
    read_only: bool
    max_retries: int
    dry_run: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_git(cwd: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise DelegationError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def current_branch(cwd: Path) -> str:
    return run_git(cwd, ["branch", "--show-current"])


def repo_default_branch(repo_root: Path) -> str:
    try:
        value = run_git(repo_root, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
        if value.startswith("origin/"):
            return value.removeprefix("origin/")
    except DelegationError:
        pass

    for name in ("main", "master", "develop"):
        try:
            run_git(repo_root, ["rev-parse", "--verify", name])
            return name
        except DelegationError:
            pass

    try:
        return run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    except DelegationError:
        return "main"


def git_root(cwd: Path) -> Path:
    return Path(run_git(cwd, ["rev-parse", "--show-toplevel"])).resolve()


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_scope(request: DelegationRequest) -> dict[str, str]:
    repo_root = request.repo_root.resolve()
    cwd = request.cwd.resolve()
    if not cwd.exists():
        raise DelegationError(f"cwd does not exist: {cwd}")
    if not is_inside(cwd, repo_root):
        raise DelegationError(f"cwd is outside repo root: {cwd}")

    branch = current_branch(cwd)
    default_branch = repo_default_branch(repo_root)
    in_worktree = ".worktrees" in cwd.parts

    outside_phase_worktree = branch == default_branch or not in_worktree

    if not request.allow_main:
        if branch == default_branch:
            raise DelegationError(
                f"refusing Codex delegation on default branch '{default_branch}'"
            )
        if not in_worktree:
            raise DelegationError("refusing Codex delegation outside .worktrees/")
    elif outside_phase_worktree and not request.read_only:
        raise DelegationError("--allow-main is only valid for read-only delegation")

    if request.read_only and request.sandbox != "read-only":
        raise DelegationError("read-only delegation requires --sandbox read-only")

    return {
        "branch": branch,
        "default_branch": default_branch,
        "cwd": str(cwd),
        "repo_root": str(repo_root),
    }


def codex_available(codex_bin: str) -> tuple[bool, str]:
    resolved = shutil.which(codex_bin) if os.path.basename(codex_bin) == codex_bin else codex_bin
    if not resolved:
        return False, f"codex binary not found: {codex_bin}"
    result = subprocess.run(
        [resolved, "app-server", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or "codex app-server is unavailable"
    return True, resolved


def ledger_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / "agents" / "reports" / "codex-delegation" / f"{task_id}.json"


def write_ledger(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def build_developer_instructions(request: DelegationRequest) -> str:
    return "\n".join(
        [
            f"You are acting as the WUR specialist role: {request.role}.",
            "Stay inside the assigned scope and current worktree.",
            "Do not merge branches, close phases, run /wur:done, or mark Work Units done.",
            "Return a concise summary, verification evidence, files touched, and any blockers.",
        ]
    )


def build_thread_start_request(
    request_id: int, request: DelegationRequest, scope: dict[str, str]
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "cwd": scope["cwd"],
        "approvalPolicy": request.approval_policy,
        "sandbox": request.sandbox,
        "serviceName": request.service_name,
        "threadSource": "subagent",
        "personality": "pragmatic",
        "developerInstructions": build_developer_instructions(request),
    }
    if request.model:
        params["model"] = request.model
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": APP_SERVER_METHOD_THREAD_START,
        "params": params,
    }


def build_turn_start_request(
    request_id: int, thread_id: str, request: DelegationRequest, scope: dict[str, str]
) -> dict[str, Any]:
    prompt = "\n\n".join(
        [
            f"WUR phase: {request.phase or 'unknown'}",
            f"WUR work unit: {request.work_unit or 'unknown'}",
            f"Git branch: {scope['branch']}",
            "Task:",
            request.prompt,
        ]
    )
    params: dict[str, Any] = {
        "threadId": thread_id,
        "cwd": scope["cwd"],
        "input": [{"type": "text", "text": prompt}],
        "approvalPolicy": request.approval_policy,
    }
    if request.model:
        params["model"] = request.model
    if request.effort:
        params["effort"] = request.effort
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": APP_SERVER_METHOD_TURN_START,
        "params": params,
    }


def extract_thread_id(thread_result: dict[str, Any]) -> str | None:
    nested = thread_result.get("thread")
    if isinstance(nested, dict) and isinstance(nested.get("id"), str):
        return nested["id"]
    value = thread_result.get("id")
    return value if isinstance(value, str) else None


def is_rate_limit_error(error: dict[str, Any] | None) -> bool:
    if not error:
        return False
    message = str(error.get("message", "")).lower()
    if "rate limit" in message or "429" in message or "usage limit" in message:
        return True
    info = error.get("codexErrorInfo")
    if isinstance(info, str):
        return info in RATE_LIMIT_KINDS
    if isinstance(info, dict):
        for value in info.values():
            if isinstance(value, dict) and value.get("httpStatusCode") in RATE_LIMIT_CODES:
                return True
    return False


def extract_final_text(turn: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in turn.get("items", []):
        if not isinstance(item, dict):
            continue
        for key in ("text", "message", "result", "review"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    return "\n\n".join(parts)


class JsonlAppServerClient:
    def __init__(self, command: list[str], cwd: Path, *, initialize: bool = True) -> None:
        self.command = command
        self.cwd = cwd
        self.initialize = initialize
        self.process: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str] = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def __enter__(self) -> "JsonlAppServerClient":
        self.process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._reader_thread = threading.Thread(
            target=self._read_stdout_lines,
            name="wur-codex-app-server-stdout",
            daemon=True,
        )
        self._reader_thread.start()
        if self.initialize:
            self.request(
                {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": APP_SERVER_METHOD_INITIALIZE,
                    "params": {
                        "clientInfo": {
                            "name": "wur-codex-delegate",
                            "title": "WUR Codex Delegation",
                            "version": "1",
                        },
                        "capabilities": {"experimentalApi": True},
                    },
                },
                time.monotonic() + 10,
            )
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            if pipe is not None and not pipe.closed:
                pipe.close()

    def _read_stdout_lines(self) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for line in self.process.stdout:
            self._stdout_queue.put(line)

    def send(self, payload: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise DelegationError("app-server process is not running")
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

    def read_message(self, deadline: float) -> dict[str, Any]:
        if self.process is None:
            raise DelegationError("app-server process is not running")
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                line = self._stdout_queue.get(timeout=min(0.2, remaining))
                return json.loads(line)
            except queue.Empty:
                pass
            if self.process.poll() is not None:
                stderr = ""
                if self.process.stderr is not None:
                    stderr = self.process.stderr.read()
                raise DelegationError(
                    f"codex app-server exited early: {stderr.strip()}"
                )
            time.sleep(0.05)
        raise TimeoutError("timed out waiting for codex app-server")

    def request(self, payload: dict[str, Any], deadline: float) -> dict[str, Any]:
        self.send(payload)
        request_id = payload["id"]
        while True:
            message = self.read_message(deadline)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise AppServerRequestError(message["error"])
            return message.get("result", {})

    def wait_for_turn(self, thread_id: str, deadline: float) -> dict[str, Any]:
        while True:
            message = self.read_message(deadline)
            if message.get("method") != APP_SERVER_TURN_COMPLETED:
                continue
            params = message.get("params", {})
            if params.get("threadId") == thread_id:
                return params.get("turn", {})


def cleanup_codex_thread(
    client: JsonlAppServerClient,
    thread_id: str | None,
    turn_id: str | None,
    *,
    interrupt: bool,
) -> dict[str, Any]:
    cleanup: dict[str, Any] = {"unsubscribed": False}
    if interrupt and turn_id:
        try:
            client.send(
                {
                    "jsonrpc": "2.0",
                    "id": 98,
                    "method": APP_SERVER_METHOD_TURN_INTERRUPT,
                    "params": {"turnId": turn_id},
                }
            )
            cleanup["interrupted"] = True
        except Exception as exc:  # noqa: BLE001 - cleanup must not mask root cause
            cleanup["interrupted"] = False
            cleanup["interrupt_error"] = str(exc)
    if thread_id:
        try:
            client.request(
                {
                    "jsonrpc": "2.0",
                    "id": 99,
                    "method": APP_SERVER_METHOD_THREAD_UNSUBSCRIBE,
                    "params": {"threadId": thread_id},
                },
                time.monotonic() + 5,
            )
            cleanup["unsubscribed"] = True
        except Exception as exc:  # noqa: BLE001 - ledger should preserve cleanup issues
            cleanup["unsubscribed"] = False
            cleanup["unsubscribe_error"] = str(exc)
    return cleanup


def run_once(
    request: DelegationRequest, codex_bin: str, task_id: str, scope: dict[str, str]
) -> dict[str, Any]:
    deadline = time.monotonic() + request.timeout_seconds
    ledger = {
        "task_id": task_id,
        "status": "started",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "role": request.role,
        "phase": request.phase,
        "work_unit": request.work_unit,
        "cwd": scope["cwd"],
        "branch": scope["branch"],
        "model": request.model,
        "sandbox": request.sandbox,
        "approval_policy": request.approval_policy,
        "service_name": request.service_name,
        "thread_id": None,
        "turn_id": None,
        "result": None,
        "error": None,
    }
    path = ledger_path(request.repo_root, task_id)
    write_ledger(path, ledger)

    if request.dry_run:
        ledger.update({"status": "dry-run", "updated_at": utc_now()})
        write_ledger(path, ledger)
        return ledger

    command = [codex_bin, "app-server", "--listen", "stdio://"]
    thread_id: str | None = None
    turn_id: str | None = None
    try:
        with JsonlAppServerClient(command, request.cwd) as client:
            try:
                thread_result = client.request(
                    build_thread_start_request(1, request, scope), deadline
                )
                thread_id = extract_thread_id(thread_result)
                if not thread_id:
                    raise DelegationError("thread/start response did not include thread.id")
                ledger.update({"thread_id": thread_id, "status": "thread-started"})
                write_ledger(path, ledger)

                turn_result = client.request(
                    build_turn_start_request(2, thread_id, request, scope), deadline
                )
                turn_id = turn_result.get("turn", {}).get("id")
                ledger.update({"turn_id": turn_id, "status": "turn-started"})
                write_ledger(path, ledger)

                turn = client.wait_for_turn(thread_id, deadline)
                status = turn.get("status")
                error = turn.get("error")
                if status != "completed":
                    if is_rate_limit_error(error):
                        ledger_status = "rate-limited"
                    else:
                        ledger_status = "failed"
                    ledger.update({"status": ledger_status, "error": error})
                else:
                    ledger.update(
                        {
                            "status": "completed",
                            "result": extract_final_text(turn),
                            "error": None,
                        }
                    )
                ledger["updated_at"] = utc_now()
                ledger.update(
                    cleanup_codex_thread(
                        client, thread_id, turn_id, interrupt=False
                    )
                )
            except TimeoutError:
                ledger.update(
                    cleanup_codex_thread(client, thread_id, turn_id, interrupt=True)
                )
                raise
            except Exception:
                ledger.update(
                    cleanup_codex_thread(client, thread_id, turn_id, interrupt=False)
                )
                raise
    except TimeoutError as exc:
        ledger.update({"status": "timeout", "error": {"message": str(exc)}})
    except AppServerRequestError as exc:
        ledger.update(
            {
                "status": "rate-limited" if is_rate_limit_error(exc.error) else "failed",
                "error": exc.error,
            }
        )
    except DelegationError as exc:
        ledger.update({"status": "failed", "error": {"message": str(exc)}})
    finally:
        ledger["thread_id"] = thread_id or ledger.get("thread_id")
        ledger["turn_id"] = turn_id or ledger.get("turn_id")
        ledger["updated_at"] = utc_now()
        write_ledger(path, ledger)
    return ledger


def run_with_retries(
    request: DelegationRequest, codex_bin: str, task_id: str, scope: dict[str, str]
) -> dict[str, Any]:
    attempts = 0
    result: dict[str, Any] = {}
    while attempts <= request.max_retries:
        result = run_once(request, codex_bin, task_id, scope)
        if result.get("status") != "rate-limited":
            return result
        if attempts == request.max_retries:
            return result
        sleep_seconds = min(60, (2**attempts) + random.random())
        time.sleep(sleep_seconds)
        attempts += 1
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delegate one scoped WUR task to Codex App Server.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="WUR ledger repo root. Defaults to the git root of --cwd.",
    )
    parser.add_argument("--cwd", required=True, help="Worktree directory for Codex.")
    parser.add_argument("--role", required=True, help="Specialist role name.")
    parser.add_argument("--prompt", required=True, help="Task prompt for Codex.")
    parser.add_argument("--phase", default=None, help="WUR phase id.")
    parser.add_argument("--work-unit", default=None, help="WUR work unit id.")
    parser.add_argument("--model", default=None, help="Optional Codex model override.")
    parser.add_argument("--effort", default=None, help="Optional reasoning effort.")
    parser.add_argument(
        "--sandbox",
        default="workspace-write",
        choices=["read-only", "workspace-write", "danger-full-access"],
    )
    parser.add_argument(
        "--approval-policy",
        default="never",
        choices=["untrusted", "on-failure", "on-request", "never"],
    )
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--service-name", default="wur-codex-delegation")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--allow-main", action="store_true")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    cwd = Path(args.cwd).resolve()
    try:
        repo_root = Path(args.repo_root).resolve() if args.repo_root else git_root(cwd)
    except DelegationError:
        repo_root = Path(args.repo_root or ".").resolve()

    request = DelegationRequest(
        repo_root=repo_root,
        cwd=cwd,
        role=args.role,
        prompt=args.prompt,
        phase=args.phase,
        work_unit=args.work_unit,
        model=args.model,
        effort=args.effort,
        sandbox=args.sandbox,
        approval_policy=args.approval_policy,
        timeout_seconds=args.timeout_seconds,
        service_name=args.service_name,
        allow_main=args.allow_main,
        read_only=args.read_only,
        max_retries=args.max_retries,
        dry_run=args.dry_run,
    )
    task_id = f"codex-{uuid.uuid4().hex[:12]}"
    try:
        scope = validate_scope(request)
        ok, codex_or_error = codex_available(args.codex_bin)
        if not ok:
            raise DelegationError(codex_or_error)
        result = run_with_retries(request, codex_or_error, task_id, scope)
    except DelegationError as exc:
        result = {
            "task_id": task_id,
            "status": "blocked",
            "error": {"message": str(exc)},
            "updated_at": utc_now(),
        }
        try:
            write_ledger(ledger_path(request.repo_root, task_id), result)
        except OSError:
            pass

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"[{result.get('status')}] {result.get('task_id')}")
        if result.get("error"):
            print(result["error"])
    return 0 if result.get("status") in {"completed", "dry-run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
