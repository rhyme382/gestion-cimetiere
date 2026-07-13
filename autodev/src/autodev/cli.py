from pathlib import Path
import shutil
import subprocess

import typer
from rich.console import Console
from rich.table import Table

from autodev.planner import PlanningError, plan_feature
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


if __name__ == "__main__":
    app()
