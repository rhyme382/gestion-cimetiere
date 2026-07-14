from __future__ import annotations

import sys
from pathlib import Path

from autodev.validation_baseline import (
    FAIL_NEW_REGRESSION,
    PASS,
    PASS_IMPROVED,
    PASS_WITH_BASELINE_FAILURES,
    compare_validation_results,
    extract_failures,
    run_validation_set,
)


def _result(command: str, returncode: int | None, stderr: str = "", stdout: str = "") -> dict[str, object]:
    return {
        "command": command,
        "argv": [sys.executable],
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def _payload(results: list[dict[str, object]], commands: list[str] | None = None) -> dict[str, object]:
    return {
        "label": "FULL",
        "commands": commands or [str(item["command"]) for item in results],
        "results": results,
        "status": "PASS" if all(item["returncode"] == 0 for item in results) else "FAIL",
    }


def test_compare_zero_failure_before_and_after_returns_pass() -> None:
    comparison = compare_validation_results(
        _payload([_result("pytest", 0, stdout="ok")]),
        _payload([_result("pytest", 0, stdout="ok")]),
    )

    assert comparison["status"] == PASS


def test_compare_same_failures_returns_pass_with_baseline_failures() -> None:
    failure = "FAIL src/test.ts > renders form\nError: expected true to be false"
    comparison = compare_validation_results(
        _payload([_result("npm run test", 1, stderr=failure)]),
        _payload([_result("npm run test", 1, stderr=failure)]),
    )

    assert comparison["status"] == PASS_WITH_BASELINE_FAILURES


def test_compare_less_failures_returns_pass_improved() -> None:
    baseline = "FAIL src/test.ts > renders form\nFAIL src/test.ts > saves change"
    post = "FAIL src/test.ts > renders form"
    comparison = compare_validation_results(
        _payload([_result("npm run test", 1, stderr=baseline)]),
        _payload([_result("npm run test", 1, stderr=post)]),
    )

    assert comparison["status"] == PASS_IMPROVED


def test_compare_new_failure_returns_fail_new_regression() -> None:
    comparison = compare_validation_results(
        _payload([_result("npm run test", 0, stdout="ok")]),
        _payload([_result("npm run test", 1, stderr="FAIL src/test.ts > renders form")]),
    )

    assert comparison["status"] == FAIL_NEW_REGRESSION


def test_missing_dependency_before_and_after_is_persistent_baseline() -> None:
    message = "Error: Cannot find module '@testing-library/dom'"
    comparison = compare_validation_results(
        _payload([_result("npm run test", 1, stderr=message)]),
        _payload([_result("npm run test", 1, stderr=message)]),
    )

    assert comparison["status"] == PASS_WITH_BASELINE_FAILURES
    assert comparison["persistent_failures"][0]["kind"] == "MISSING_DEPENDENCY"


def test_missing_dependency_only_after_is_new_regression() -> None:
    comparison = compare_validation_results(
        _payload([_result("npm run test", 0, stdout="ok")]),
        _payload([_result("npm run test", 1, stderr="Error: Cannot find module '@testing-library/dom'")]),
    )

    assert comparison["status"] == FAIL_NEW_REGRESSION
    assert comparison["new_failures"][0]["kind"] == "MISSING_DEPENDENCY"


def test_extract_failures_normalizes_absolute_paths() -> None:
    failures = extract_failures(
        [
            _result(
                "pytest",
                1,
                stderr="FAIL /tmp/project/tests/test_sample.py > case\nAssertionError: /tmp/project/src/app.py failed",
            )
        ]
    )

    assert "<ABS_PATH>" in failures[0]["signature"]
    assert "/tmp/project" not in failures[0]["signature"]


def test_extract_failures_strips_ansi_codes() -> None:
    failures = extract_failures(
        [
            _result(
                "pytest",
                1,
                stderr="\x1b[31mFAIL src/test_sample.py > case\x1b[0m\n\x1b[31mError: boom\x1b[0m",
            )
        ]
    )

    assert "\x1b" not in failures[0]["signature"]


def test_run_validation_set_writes_artifacts(tmp_path: Path) -> None:
    payload = run_validation_set(
        tmp_path,
        [f"{sys.executable} -c \"raise SystemExit(1)\""],
        tmp_path / "validation",
        label="FULL",
    )

    assert payload["status"] == "FAIL"
    assert (tmp_path / "validation" / "validation-results.json").is_file()
    assert (tmp_path / "validation" / "failures.json").is_file()
