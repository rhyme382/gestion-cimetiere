from pathlib import Path
import shutil
import subprocess

import typer
from rich.console import Console
from rich.table import Table

from autodev.feature_status import FeatureStatusError, read_feature_status
from autodev.integrate_task import IntegrateTaskError, integrate_task
from autodev.planner import PlanningError, plan_feature
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
    table.add_row("Tâches intégrées", ", ".join(status["tasks_integrated"]) or "—")
    table.add_row("Tâche courante", status["current_task_id"] or "—")
    table.add_row("Dernière action", status["last_action"] or "—")
    table.add_row("Dernier verdict", status["last_verdict"] or "—")
    table.add_row("Corrections", str(status["correction_count"]))
    table.add_row("Worktrees", ", ".join(status["worktrees"]) or "—")
    table.add_row("États incohérents", " | ".join(status["inconsistencies"]) or "—")
    table.add_row("Rapports", status["reports_path"])
    console.print(table)


if __name__ == "__main__":
    app()
