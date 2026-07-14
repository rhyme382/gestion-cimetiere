from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from autodev.task_runner import RunTaskError, validate_command_safe, write_json

PASS = "PASS"
PASS_WITH_BASELINE_FAILURES = "PASS_WITH_BASELINE_FAILURES"
PASS_IMPROVED = "PASS_IMPROVED"
FAIL_NEW_REGRESSION = "FAIL_NEW_REGRESSION"
ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
INDETERMINATE = "INDETERMINATE"

TEST_FAILURE = "TEST_FAILURE"
BUILD_FAILURE = "BUILD_FAILURE"
LINT_FAILURE = "LINT_FAILURE"
MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
TOOL_MISSING = "TOOL_MISSING"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
UNKNOWN_ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
UNKNOWN = "UNKNOWN"

COMPARABLE_FAILURE_KINDS = {
    TEST_FAILURE,
    BUILD_FAILURE,
    LINT_FAILURE,
    MISSING_DEPENDENCY,
    UNKNOWN,
}
BLOCKING_ENVIRONMENT_KINDS = {
    TOOL_MISSING,
    CONFIGURATION_ERROR,
    UNKNOWN_ENVIRONMENT_ERROR,
}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
UNIX_ABS_PATH_RE = re.compile(r"(?<![\w.])/(?:[^\s:/]+/)*[^\s:]+")
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:\\(?:[^\\\s:]+\\)*[^\\\s:]+")
PID_RE = re.compile(r"\bpid\s+\d+\b", re.IGNORECASE)
TIME_RE = re.compile(r"\b\d+(?:\.\d+)?(?:ms|s|m)\b")
STACK_LINE_RE = re.compile(r"^\s+at\s+")


def load_quality_gates(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "autodev" / "config" / "quality-gates.yaml"
    if not path.is_file():
        raise RunTaskError(f"Configuration quality gates introuvable : {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise RunTaskError("Le fichier quality-gates.yaml doit contenir un objet YAML.")

    for level in ("task", "smoke", "full"):
        payload.setdefault(level, {})
    for level in ("smoke", "full"):
        commands = payload[level].get("commands", [])
        if not isinstance(commands, list) or not all(isinstance(item, str) for item in commands):
            raise RunTaskError(f"Les commandes du niveau {level} sont invalides.")
    return payload


def run_validation_set(
    worktree: Path,
    commands: list[str],
    output_dir: Path,
    *,
    label: str,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for command in commands:
        try:
            argv = validate_command_safe(command)
        except RunTaskError as exc:
            results.append(
                {
                    "command": command,
                    "argv": [],
                    "returncode": None,
                    "stdout": "",
                    "stderr": str(exc),
                    "execution_error": exc.__class__.__name__,
                }
            )
            continue

        try:
            completed = subprocess.run(
                argv,
                cwd=worktree,
                capture_output=True,
                text=True,
                check=False,
                env=None if extra_env is None else {**os.environ, **extra_env},
            )
            results.append(
                {
                    "command": command,
                    "argv": argv,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            )
        except OSError as exc:
            results.append(
                {
                    "command": command,
                    "argv": argv,
                    "returncode": None,
                    "stdout": "",
                    "stderr": str(exc),
                    "execution_error": exc.__class__.__name__,
                }
            )

    payload = {
        "label": label,
        "commands": list(commands),
        "results": results,
        "status": PASS if all(item.get("returncode") == 0 for item in results) else "FAIL",
    }
    failures = extract_failures(results)

    write_json(output_dir / "validation-results.json", payload)
    write_json(output_dir / "failures.json", failures)
    (output_dir / "stdout.log").write_text(render_stream(results, "stdout"), encoding="utf-8")
    (output_dir / "stderr.log").write_text(render_stream(results, "stderr"), encoding="utf-8")
    return payload


def extract_failures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for result in results:
        if result.get("returncode") == 0:
            continue
        failures.extend(_extract_result_failures(result))
    return failures


def compare_validation_results(
    baseline_results: dict[str, Any],
    post_merge_results: dict[str, Any],
) -> dict[str, Any]:
    baseline_failures = extract_failures(list(baseline_results.get("results", [])))
    post_failures = extract_failures(list(post_merge_results.get("results", [])))

    baseline_commands = list(baseline_results.get("commands", []))
    post_commands = list(post_merge_results.get("commands", []))
    if baseline_commands != post_commands:
        return {
            "status": INDETERMINATE,
            "baseline_failure_count": len(baseline_failures),
            "post_merge_failure_count": len(post_failures),
            "persistent_failures": [],
            "resolved_failures": [],
            "new_failures": [],
            "environment_failures": [],
            "summary": "Les commandes FULL diffèrent entre la baseline et le post-merge.",
        }

    environment_failures = [
        failure
        for failure in [*baseline_failures, *post_failures]
        if failure["kind"] in BLOCKING_ENVIRONMENT_KINDS
    ]
    if environment_failures:
        comparison = {
            "status": ENVIRONMENT_ERROR,
            "baseline_failure_count": len(baseline_failures),
            "post_merge_failure_count": len(post_failures),
            "persistent_failures": [],
            "resolved_failures": [],
            "new_failures": [],
            "environment_failures": dedupe_failures(environment_failures),
        }
        comparison["summary"] = build_comparison_summary(comparison)
        return comparison

    baseline_index = {failure["signature"]: failure for failure in baseline_failures}
    post_index = {failure["signature"]: failure for failure in post_failures}

    baseline_signatures = set(baseline_index)
    post_signatures = set(post_index)

    persistent = [baseline_index[sig] for sig in sorted(baseline_signatures & post_signatures)]
    resolved = [baseline_index[sig] for sig in sorted(baseline_signatures - post_signatures)]
    new = [post_index[sig] for sig in sorted(post_signatures - baseline_signatures)]

    comparison = {
        "status": "",
        "baseline_failure_count": len(baseline_failures),
        "post_merge_failure_count": len(post_failures),
        "persistent_failures": persistent,
        "resolved_failures": resolved,
        "new_failures": new,
        "environment_failures": [],
    }
    comparison["status"] = classify_validation_outcome(comparison)
    comparison["summary"] = build_comparison_summary(comparison)
    return comparison


def classify_validation_outcome(comparison: dict[str, Any]) -> str:
    if comparison.get("environment_failures"):
        return ENVIRONMENT_ERROR

    if comparison.get("status") == INDETERMINATE:
        return INDETERMINATE

    baseline_count = int(comparison.get("baseline_failure_count", 0))
    post_count = int(comparison.get("post_merge_failure_count", 0))
    persistent = list(comparison.get("persistent_failures", []))
    resolved = list(comparison.get("resolved_failures", []))
    new = list(comparison.get("new_failures", []))

    if baseline_count == 0 and post_count == 0:
        return PASS
    if new:
        return FAIL_NEW_REGRESSION
    if resolved:
        return PASS_IMPROVED
    if persistent:
        return PASS_WITH_BASELINE_FAILURES
    return INDETERMINATE


def build_comparison_summary(comparison: dict[str, Any]) -> str:
    status = comparison.get("status", INDETERMINATE)
    if status == PASS:
        return "Aucun échec avant ou après intégration."
    if status == PASS_WITH_BASELINE_FAILURES:
        return "Les échecs post-merge sont strictement identiques à la baseline."
    if status == PASS_IMPROVED:
        return "Des échecs baseline ont disparu sans nouvelle régression."
    if status == FAIL_NEW_REGRESSION:
        return "Au moins une nouvelle signature d'échec apparaît après intégration."
    if status == ENVIRONMENT_ERROR:
        return "La comparaison n'est pas fiable à cause d'une erreur d'environnement."
    return "Les résultats de validation ne peuvent pas être comparés de manière fiable."


def dedupe_failures(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for failure in failures:
        unique.setdefault(failure["signature"], failure)
    return [unique[key] for key in sorted(unique)]


def render_stream(results: list[dict[str, Any]], stream: str) -> str:
    chunks: list[str] = []
    for item in results:
        payload = str(item.get(stream, ""))
        if not payload:
            continue
        chunks.append(f"$ {item['command']}\n{payload}")
    return "".join(f"{chunk}\n" for chunk in chunks)


def _extract_result_failures(result: dict[str, Any]) -> list[dict[str, Any]]:
    command = str(result.get("command", ""))
    output = normalize_message(
        "\n".join(
            part for part in [str(result.get("stdout", "")), str(result.get("stderr", ""))] if part
        )
    )
    kind = classify_failure_kind(command, output, result)
    base_failure = build_failure(
        command=command,
        kind=kind,
        suite=None,
        test_name=None,
        message=select_representative_message(output, command),
    )

    if kind not in {TEST_FAILURE, MISSING_DEPENDENCY}:
        return [base_failure]

    parsed = parse_test_failures(command, output, fallback_kind=kind)
    return parsed or [base_failure]


def parse_test_failures(command: str, output: str, *, fallback_kind: str) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or STACK_LINE_RE.match(raw_line):
            continue
        if line.startswith("FAIL "):
            detail = line[5:].strip()
            parts = [part.strip() for part in detail.split(" > ") if part.strip()]
            suite = parts[0] if parts else None
            test_name = " > ".join(parts[1:]) if len(parts) > 1 else None
            failures.append(
                build_failure(
                    command=command,
                    kind=fallback_kind,
                    suite=suite,
                    test_name=test_name,
                    message=detail,
                )
            )
        elif line.startswith(("× ", "✕ ")):
            failures.append(
                build_failure(
                    command=command,
                    kind=fallback_kind,
                    suite=None,
                    test_name=line[2:].strip(),
                    message=line[2:].strip(),
                )
            )

    return dedupe_failures(failures)


def build_failure(
    *,
    command: str,
    kind: str,
    suite: str | None,
    test_name: str | None,
    message: str,
) -> dict[str, Any]:
    normalized_message = normalize_message(message)
    signature_parts = [
        normalize_message(command),
        suite or "<no-suite>",
        test_name or "<no-test>",
        kind,
        normalized_message,
    ]
    return {
        "command": command,
        "suite": suite,
        "test_name": test_name,
        "kind": kind,
        "message": normalized_message,
        "signature": "|".join(signature_parts),
    }


def classify_failure_kind(command: str, output: str, result: dict[str, Any]) -> str:
    lowered_command = command.lower()
    lowered_output = output.lower()

    if result.get("execution_error"):
        return TOOL_MISSING
    if "command not found" in lowered_output or "not recognized as an internal or external command" in lowered_output:
        return TOOL_MISSING
    if "no such file or directory" in lowered_output and result.get("returncode") is None:
        return TOOL_MISSING
    if "cannot find module" in lowered_output or "module not found" in lowered_output:
        return MISSING_DEPENDENCY
    if "missing script" in lowered_output or "config" in lowered_output and "error" in lowered_output:
        return CONFIGURATION_ERROR
    if "npm run build" in lowered_command or "vite build" in lowered_command or "tsc " in lowered_command:
        return BUILD_FAILURE
    if "lint" in lowered_command:
        return LINT_FAILURE
    if "test" in lowered_command or "pytest" in lowered_command or "vitest" in lowered_output or "cargo test" in lowered_command:
        return TEST_FAILURE
    return UNKNOWN


def select_representative_message(output: str, command: str) -> str:
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if STACK_LINE_RE.match(raw_line):
            continue
        return line
    return command


def normalize_message(message: str) -> str:
    sanitized = ANSI_RE.sub("", message)
    sanitized = WINDOWS_ABS_PATH_RE.sub("<ABS_PATH>", sanitized)
    sanitized = UNIX_ABS_PATH_RE.sub("<ABS_PATH>", sanitized)
    sanitized = PID_RE.sub("pid <PID>", sanitized)
    sanitized = TIME_RE.sub("<TIME>", sanitized)
    lines = [re.sub(r"\s+", " ", line).strip() for line in sanitized.splitlines()]
    normalized_lines = [line for line in lines if line]
    return "\n".join(normalized_lines)


def comparison_to_json(comparison: dict[str, Any]) -> str:
    return json.dumps(comparison, ensure_ascii=False, indent=2) + "\n"
