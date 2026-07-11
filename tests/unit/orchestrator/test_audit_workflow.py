from __future__ import annotations

import json
from pathlib import Path

from orchestrator import cli
from orchestrator.runners.codex_runner import CodexRunResult


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    _write(repo / "SPEC.md", "# spec\n")
    _write(repo / "ROADMAP.md", "# roadmap\n")
    _write(repo / "AGENTS.md", "# agents\n")
    _write(repo / "agents/STATUS.md", "# status\n")
    _write(repo / "agents/QUEUE.md", "# queue\n")
    _write(repo / "orchestrator/prompts/product_audit.md", "Audit template\n")
    _write(repo / "src/App.tsx", "export function App() { return null; }\n")
    _write(repo / "src-tauri/src/main.rs", "fn main() {}\n")
    _write(repo / "src-tauri/migrations/001.sql", "-- migration\n")
    _write(repo / "src-tauri/tests/integration.rs", "#[test]\nfn ok() {}\n")
    _write(repo / "tests/e2e/sample.spec.ts", "test('ok', () => {});\n")
    _write(repo / "reports/qa/report.md", "# qa\n")
    _write(repo / "package.json", "{}\n")
    _write(repo / "Cargo.toml", "[workspace]\n")
    _write(repo / "src-tauri/Cargo.toml", "[package]\nname='x'\nversion='0.1.0'\n")
    _write(repo / "src-tauri/tauri.conf.json", "{}\n")
    _write(repo / "playwright.config.ts", "export default {};\n")
    _write(repo / ".github/workflows/release-v0.1-artifacts.yml", "name: release\n")
    return repo


def _valid_backlog() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-07-11T10:00:00Z",
        "tasks": [
            {
                "id": "AUD-001",
                "domain": "frontend",
                "title": "Rendre la recherche globale exploitable",
                "user_story": "Un agent de mairie peut rechercher un defunt depuis l'application.",
                "priority": "critical",
                "status": "pending",
                "dependencies": [],
                "recommended_agent": "claude",
                "likely_files": ["src/pages/RecherchePage.tsx"],
                "acceptance_criteria": [
                    "Depuis l'ecran de recherche, l'agent de mairie peut rechercher un defunt sans terminal."
                ],
                "required_unit_tests": ["vitest: recherche globale"],
                "required_e2e_test": "Playwright: recherche globale depuis l'interface",
                "required_ui_evidence": "Capture de l'ecran de recherche avec resultat visible",
                "definition_of_done": ["La recherche fonctionne dans l'application packagee."],
            }
        ],
    }


class FakeCodexRunner:
    def __init__(self, writer=None, *, returncode=0, timed_out=False):
        self.writer = writer
        self.returncode = returncode
        self.timed_out = timed_out
        self.calls = []

    def run(self, prompt, *, cwd, timeout, log_dir):
        self.calls.append({"prompt": prompt, "cwd": cwd, "timeout": timeout, "log_dir": str(log_dir)})
        if self.writer is not None:
            self.writer(Path(cwd))
        return CodexRunResult(
            command=["codex", "exec"],
            prompt=prompt,
            returncode=None if self.timed_out else self.returncode,
            stdout="",
            stderr="",
            duration_seconds=0.1,
            session_id="sess-1",
            log_dir=str(log_dir),
            timed_out=self.timed_out,
        )


def test_audit_dry_run(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, dry_run=True, verbose=True)
    output = json.loads(capsys.readouterr().out)

    assert code == 0
    assert output["status"] == "AUDIT_DRY_RUN"
    assert output["source_summary"]["frontend"] == 1
    assert "tasks/backlog.json" in output["required_outputs"]


def test_audit_success(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    def writer(root: Path):
        _write(root / "product/FEATURE_MATRIX.md", "# matrix\n")
        _write(root / "product/GAP_ANALYSIS.md", "# gaps\n")
        _write(root / "product/USER_JOURNEYS.md", "# journeys\n")
        _write(root / "product/ALPHA_ROADMAP.md", "# roadmap\n")
        _write(root / "reports/product/PRODUCT_AUDIT_REPORT.md", "# report\n")
        _write(root / "tasks/backlog.json", json.dumps(_valid_backlog()))

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 0
    assert output["status"] == "AUDIT_COMPLETED"
    assert output["task_count"] == 1
    assert output["domain_count"] == 1
    assert output["critical_gap_count"] == 1


def test_audit_codex_non_zero(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(returncode=2))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_CODEX"


def test_audit_timeout(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(timed_out=True))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_TIMEOUT"


def test_audit_missing_output(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    def writer(root: Path):
        _write(root / "product/FEATURE_MATRIX.md", "# matrix\n")

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_MISSING_OUTPUT"


def test_audit_invalid_backlog_json(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    def writer(root: Path):
        for path in (
            "product/FEATURE_MATRIX.md",
            "product/GAP_ANALYSIS.md",
            "product/USER_JOURNEYS.md",
            "product/ALPHA_ROADMAP.md",
            "reports/product/PRODUCT_AUDIT_REPORT.md",
        ):
            _write(root / path, "# ok\n")
        _write(root / "tasks/backlog.json", "{invalid")

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_INVALID_BACKLOG"


def test_audit_empty_backlog(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    def writer(root: Path):
        for path in (
            "product/FEATURE_MATRIX.md",
            "product/GAP_ANALYSIS.md",
            "product/USER_JOURNEYS.md",
            "product/ALPHA_ROADMAP.md",
            "reports/product/PRODUCT_AUDIT_REPORT.md",
        ):
            _write(root / path, "# ok\n")
        _write(root / "tasks/backlog.json", json.dumps({"schema_version": "1.0", "generated_at": "2026-07-11T10:00:00Z", "tasks": []}))

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_EMPTY_BACKLOG"


def test_audit_duplicate_ids(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    def writer(root: Path):
        payload = _valid_backlog()
        payload["tasks"].append(dict(payload["tasks"][0]))
        for path in (
            "product/FEATURE_MATRIX.md",
            "product/GAP_ANALYSIS.md",
            "product/USER_JOURNEYS.md",
            "product/ALPHA_ROADMAP.md",
            "reports/product/PRODUCT_AUDIT_REPORT.md",
        ):
            _write(root / path, "# ok\n")
        _write(root / "tasks/backlog.json", json.dumps(payload))

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_INVALID_BACKLOG"


def test_audit_unknown_dependency(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})

    def writer(root: Path):
        payload = _valid_backlog()
        payload["tasks"][0]["dependencies"] = ["AUD-999"]
        for path in (
            "product/FEATURE_MATRIX.md",
            "product/GAP_ANALYSIS.md",
            "product/USER_JOURNEYS.md",
            "product/ALPHA_ROADMAP.md",
            "reports/product/PRODUCT_AUDIT_REPORT.md",
        ):
            _write(root / path, "# ok\n")
        _write(root / "tasks/backlog.json", json.dumps(payload))

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_INVALID_BACKLOG"


def test_audit_unauthorized_change_in_src(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    snapshots = iter([{}, {"src/App.tsx": " M", "product/FEATURE_MATRIX.md": "??"}])
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: next(snapshots))

    def writer(root: Path):
        _write(root / "product/FEATURE_MATRIX.md", "# matrix\n")
        _write(root / "product/GAP_ANALYSIS.md", "# gaps\n")
        _write(root / "product/USER_JOURNEYS.md", "# journeys\n")
        _write(root / "product/ALPHA_ROADMAP.md", "# roadmap\n")
        _write(root / "reports/product/PRODUCT_AUDIT_REPORT.md", "# report\n")
        _write(root / "tasks/backlog.json", json.dumps(_valid_backlog()))

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_FAILED_UNAUTHORIZED_CHANGES"
    assert output["unauthorized_changes"] == ["src/App.tsx"]


def test_audit_refuses_overwrite_without_force(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    _write(repo / "product/FEATURE_MATRIX.md", "# existing\n")

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, codex_runner=FakeCodexRunner())
    output = json.loads(capsys.readouterr().out)

    assert code == 1
    assert output["status"] == "AUDIT_ALREADY_EXISTS"


def test_audit_force_archives_existing_outputs(monkeypatch, tmp_path, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "snapshot_git_status", lambda _: {})
    _write(repo / "product/FEATURE_MATRIX.md", "# existing\n")
    _write(repo / "reports/product/PRODUCT_AUDIT_REPORT.md", "# existing report\n")

    def writer(root: Path):
        _write(root / "product/FEATURE_MATRIX.md", "# matrix\n")
        _write(root / "product/GAP_ANALYSIS.md", "# gaps\n")
        _write(root / "product/USER_JOURNEYS.md", "# journeys\n")
        _write(root / "product/ALPHA_ROADMAP.md", "# roadmap\n")
        _write(root / "reports/product/PRODUCT_AUDIT_REPORT.md", "# report\n")
        _write(root / "tasks/backlog.json", json.dumps(_valid_backlog()))

    code = cli.command_audit(Path("ignored"), Path("ignored"), {}, force=True, codex_runner=FakeCodexRunner(writer))
    output = json.loads(capsys.readouterr().out)

    assert code == 0
    assert output["status"] == "AUDIT_COMPLETED"
    archive_path = Path(output["archive_path"])
    assert (archive_path / "product/FEATURE_MATRIX.md").exists()
    assert (archive_path / "reports/product/PRODUCT_AUDIT_REPORT.md").exists()
