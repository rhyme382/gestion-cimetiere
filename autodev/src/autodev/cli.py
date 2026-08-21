import json
from pathlib import Path
import shutil
import subprocess

import typer
from rich.console import Console
from rich.table import Table

from autodev.acceptance_criteria import (
    AcceptanceCriteriaError,
    build_coverage_matrix,
    migrate_backlog_acceptance_criteria,
    render_coverage_text,
)
from autodev.correct_task import CorrectTaskError, correct_task
from autodev.feature_status import FeatureStatusError, read_feature_status
from autodev.integrate_task import IntegrateTaskError, integrate_task
from autodev.monitor import monitor_feature
from autodev.monitor_state import MonitorStateError
from autodev.planner import PlanningError, find_repo_root, load_json, plan_feature
from autodev.product_plan import ProductPlanError, load_product_plan, freeze_plan_revision
from autodev.run_feature import RunFeatureError, run_feature
from autodev.review_task import ReviewTaskError, review_task
from autodev.task_runner import RunTaskError, run_task

app = typer.Typer(
    name="autodev",
    help="Ordonnanceur de développement autonome de Gestion de cimetière.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main() -> None:
    """Commandes de l'ordonnanceur autodev."""


def command_available(command: str) -> bool:
    return shutil.which(command) is not None


def is_git_repository(path: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


@app.command()
def doctor() -> None:
    """Vérifie le dépôt, sa structure et les outils indispensables."""
    repo_root = Path.cwd()

    checks = {
        "Dépôt Git": is_git_repository(repo_root),
        "Dossier specs": (repo_root / "specs").is_dir(),
        "Dossier autodev": (repo_root / "autodev").is_dir(),
        "État autodev": (repo_root / ".autodev").is_dir(),
        "Codex CLI": command_available("codex"),
        "Claude Code": command_available("claude"),
        "Git": command_available("git"),
    }

    failed = False

    for label, success in checks.items():
        marker = "[green]OK[/green]" if success else "[red]ÉCHEC[/red]"
        console.print(f"{marker} — {label}")
        failed = failed or not success

    if failed:
        console.print(
            "\n[bold red]La préparation du dépôt est incomplète.[/bold red]"
        )
        raise typer.Exit(code=1)

    console.print("\n[bold green]Structure autodev prête.[/bold green]")


@app.command("run-product")
def run_product_command(
    plan_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du fichier de plan produit JSON.",
    ),
    run_id: str = typer.Option(
        ...,
        "--run-id",
        help="Identifiant unique du run produit.",
    ),
) -> None:
    """Orchestre l'exécution d'un plan produit versionné avec features séquentielles."""
    console.print(f"[bold]Orchestration du plan produit {plan_path.name}[/bold]")

    try:
        plan = load_product_plan(plan_path)
    except ProductPlanError as exc:
        console.print(f"\n[bold red]Erreur plan produit :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    frozen_revision = freeze_plan_revision(plan, run_id)

    runs_dir = Path.cwd() / ".autodev" / "runs" / "products" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    journal_path = runs_dir / "journal.jsonl"
    revision_path = runs_dir / "frozen_revision.json"

    with open(journal_path, "a", encoding="utf-8") as f:
        journal_entry = {
            "timestamp": frozen_revision["frozen_at"],
            "event": "PLAN_FROZEN",
            "run_id": run_id,
            "plan_id": frozen_revision["plan_id"],
            "plan_hash": frozen_revision["plan_hash"],
            "schema_version": frozen_revision["schema_version"],
            "feature_count": frozen_revision["feature_count"],
        }
        f.write(json.dumps(journal_entry, ensure_ascii=False) + "\n")

    with open(revision_path, "w", encoding="utf-8") as f:
        json.dump(frozen_revision, f, ensure_ascii=False, indent=2)

    table = Table(title="Plan produit gelé")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Run ID", frozen_revision["run_id"])
    table.add_row("Plan ID", frozen_revision["plan_id"])
    table.add_row("Plan Hash", frozen_revision["plan_hash"][:16] + "...")
    table.add_row("Schéma", frozen_revision["schema_version"])
    table.add_row("Branche intégration", frozen_revision["integration_branch"])
    table.add_row("Nombre de features", str(frozen_revision["feature_count"]))
    table.add_row("Figé à", frozen_revision["frozen_at"])
    console.print(table)
    console.print(f"\n[bold green]Révision gelée :[/bold green] {revision_path}")
    console.print(f"[bold green]Journal :[/bold green] {journal_path}")


@app.command("plan")
def plan_command(
    specification: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du fichier de spécification Markdown.",
    ),
) -> None:
    """Transforme une spécification en backlog exécutable avec Codex."""
    console.print(f"[bold]Planification de {specification.name}[/bold]")

    try:
        output_path, backlog = plan_feature(specification)
    except PlanningError as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Backlog généré")
    table.add_column("Tâche")
    table.add_column("Agent")
    table.add_column("Titre")
    table.add_column("Dépendances")

    for task in backlog["tasks"]:
        dependencies = ", ".join(task["depends_on"]) or "—"
        table.add_row(
            task["id"],
            task["agent"],
            task["title"],
            dependencies,
        )

    console.print(table)
    console.print(
        f"\n[bold green]Backlog valide :[/bold green] {output_path}"
    )


@app.command("run-task")
def run_task_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
    task_id: str = typer.Argument(..., help="Identifiant de tâche à exécuter."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Valide la tâche et affiche le plan sans créer de worktree.",
    ),
) -> None:
    """Prépare et exécute une tâche backlog avec Claude Code."""
    try:
        summary = run_task(backlog_json=backlog_json, task_id=task_id, dry_run=dry_run)
    except RunTaskError as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Résumé run-task")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Tâche", summary["task_id"])
    table.add_row("Branche", summary["branch"])
    table.add_row("Worktree", summary["worktree"])
    table.add_row(
        "Commit produit",
        summary.get("produced_commit") or ("—" if dry_run else "aucun"),
    )
    table.add_row(
        "Chemins modifiés",
        ", ".join(summary.get("modified_paths", [])) or "—",
    )
    table.add_row(
        "Validations",
        ", ".join(summary.get("validation_summary", [])) or "—",
    )
    table.add_row("Rapports", summary["run_dir"])
    console.print(table)

    if dry_run:
        console.print("\n[bold yellow]Dry-run :[/bold yellow] aucun worktree créé.")


@app.command("review-task")
def review_task_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
    task_id: str = typer.Argument(..., help="Identifiant de tâche à relire."),
) -> None:
    """Relit une tâche développée avec Codex en lecture seule."""
    try:
        summary = review_task(backlog_json=backlog_json, task_id=task_id)
    except ReviewTaskError as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Résumé review-task")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Tâche", summary["task_id"])
    table.add_row("Verdict", summary["verdict"])
    table.add_row("Tests", summary["tests"]["status"])
    table.add_row("Scope", summary["scope"]["status"])
    table.add_row("Issues", str(len(summary["issues"])))
    table.add_row("Résumé", summary["summary"])
    console.print(table)


@app.command("correct-task")
def correct_task_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
    task_id: str = typer.Argument(..., help="Identifiant de tâche à corriger."),
    guidance_file: Path | None = typer.Option(
        None,
        "--guidance",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Fichier Markdown facultatif de consignes complémentaires du superviseur.",
    ),
) -> None:
    """Corrige une tâche revue avec Claude, avec supervision humaine facultative."""
    guidance = guidance_file.read_text(encoding="utf-8") if guidance_file else None
    try:
        summary = correct_task(
            backlog_json=backlog_json,
            task_id=task_id,
            guidance=guidance,
        )
    except (CorrectTaskError, OSError) as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Résumé correct-task")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Tâche", summary["task_id"])
    table.add_row("Statut", summary["status"])
    table.add_row("Correction", str(summary["correction_number"]))
    table.add_row("Commit produit", summary.get("produced_commit") or "—")
    table.add_row(
        "Chemins conservés",
        ", ".join(summary.get("remaining_allowed_paths", [])) or "—",
    )
    table.add_row(
        "Validations",
        ", ".join(summary.get("validation_summary", [])) or "—",
    )
    console.print(table)


@app.command("integrate-task")
def integrate_task_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
    task_id: str = typer.Argument(..., help="Identifiant de tâche à intégrer."),
) -> None:
    """Intègre une tâche approuvée dans la branche principale courante."""
    try:
        summary = integrate_task(backlog_json=backlog_json, task_id=task_id)
    except IntegrateTaskError as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Résumé integrate-task")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Tâche", summary["task_id"])
    table.add_row("Verdict préalable", summary["pre_review_verdict"] or "—")
    table.add_row("Branche cible", summary["target_branch"] or "—")
    table.add_row("Branche tâche", summary["task_branch"])
    table.add_row("Commit intégré", summary["integration_commit"] or "—")
    table.add_row(
        "Validations",
        ", ".join(summary.get("validations", [])) or "—",
    )
    table.add_row("Statut", summary["status"])
    table.add_row(
        "Rapports",
        str(Path(".autodev") / "runs" / task_id / "integration"),
    )
    console.print(table)


@app.command("run-feature")
def run_feature_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Reprend depuis le checkpoint LangGraph existant pour cette feature.",
    ),
    max_corrections: int = typer.Option(
        3,
        "--max-corrections",
        min=0,
        help="Nombre maximal de boucles de correction automatiques par tâche.",
    ),
) -> None:
    """Orchestre séquentiellement toutes les tâches d'une fonctionnalité avec LangGraph."""

    def progress(message: str) -> None:
        console.print(message)

    try:
        summary = run_feature(
            backlog_json=backlog_json,
            resume=resume,
            max_corrections=max_corrections,
            progress=progress,
        )
    except RunFeatureError as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Résumé run-feature")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Feature", summary["feature_id"])
    table.add_row("Tâches intégrées", ", ".join(summary["tasks_integrated"]) or "—")
    table.add_row("Tâches restantes", ", ".join(summary["tasks_remaining"]) or "—")
    table.add_row("Statut final", summary["status"])
    table.add_row("Checkpoints", summary["checkpoints_path"])
    table.add_row("Rapports", summary["reports_path"])
    console.print(table)


@app.command("status")
def status_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
) -> None:
    """Affiche l'état déterministe courant d'une feature autodev."""
    try:
        status = read_feature_status(backlog_json)
    except FeatureStatusError as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Statut autodev")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Feature", status["feature_id"])
    table.add_row("Titre", status["feature_title"])
    table.add_row("État", status["feature_status"])
    historical_status = status["historical_feature_status"]
    if historical_status and historical_status != status["feature_status"]:
        table.add_row("Ancien résultat d’exécution", historical_status)
    table.add_row("Tâches intégrées", ", ".join(status["tasks_integrated"]) or "—")
    table.add_row("Tâche courante", status["current_task_id"] or "—")
    table.add_row("Dernière action", status["last_action"] or "—")
    table.add_row("Dernier verdict", status["last_verdict"] or "—")
    table.add_row("Corrections", str(status["correction_count"]))
    table.add_row("Worktrees", ", ".join(status["worktrees"]) or "—")
    table.add_row("États incohérents", " | ".join(status["inconsistencies"]) or "—")
    table.add_row("Rapports", status["reports_path"])
    console.print(table)


@app.command("monitor")
def monitor_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
    refresh: float = typer.Option(
        2.0,
        "--refresh",
        min=0.5,
        help="Intervalle de rafraîchissement en secondes.",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="Affiche un instantané puis quitte.",
    ),
    logs: bool = typer.Option(
        False,
        "--logs",
        help="Affiche également les dernières lignes de logs.",
    ),
    log_lines: int = typer.Option(
        20,
        "--log-lines",
        min=1,
        help="Nombre de lignes de logs affichées.",
    ),
    no_clear: bool = typer.Option(
        False,
        "--no-clear",
        help="Ne nettoie pas le terminal entre les rafraîchissements.",
    ),
) -> None:
    """Supervise localement une feature autodev en cours."""
    try:
        monitor_feature(
            backlog_json,
            refresh=refresh,
            once=once,
            include_logs=logs,
            log_lines=log_lines,
            no_clear=no_clear,
            console=console,
        )
    except MonitorStateError as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("coverage")
def coverage_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Retourne la matrice de couverture en JSON.",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="Option acceptée pour compatibilité CLI; la commande est instantanée.",
    ),
) -> None:
    """Affiche la couverture déterministe des critères d'acceptation."""
    del once
    try:
        repo_root = find_repo_root(backlog_json.parent)
        backlog = load_json(backlog_json)
        coverage = build_coverage_matrix(backlog, repo_root)
    except (AcceptanceCriteriaError, OSError, ValueError, RuntimeError, PlanningError) as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if as_json:
        console.print_json(json.dumps(coverage, ensure_ascii=False, indent=2))
        return

    console.print(render_coverage_text(coverage))


@app.command("migrate-backlog")
def migrate_backlog_command(
    backlog_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin du backlog JSON à migrer.",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Chemin du backlog migré.",
    ),
) -> None:
    """Migre un backlog legacy vers des critères structurés propriétaires."""
    if output == backlog_json:
        console.print("\n[bold red]Échec :[/bold red] --output doit être différent du fichier source.")
        raise typer.Exit(code=1)

    try:
        backlog = load_json(backlog_json)
        migrated = migrate_backlog_acceptance_criteria(backlog)
    except (AcceptanceCriteriaError, RuntimeError, PlanningError) as exc:
        console.print(f"\n[bold red]Échec :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    console.print(f"[bold green]Backlog migré :[/bold green] {output}")


if __name__ == "__main__":
    app()
