from crewai import Agent, Task, Crew, Process
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_file(path: str) -> str:
    file_path = ROOT / path
    if not file_path.exists():
        return f"[FICHIER MANQUANT: {path}]"
    return file_path.read_text(encoding="utf-8")

spec = read_file("SPEC.md")
agents_rules = read_file("AGENTS.md")

product_owner = Agent(
    role="Product Owner logiciel métier mairie",
    goal="Transformer le cahier des charges en exigences priorisées, testables et exploitables.",
    backstory="Expert des logiciels métiers pour collectivités, cimetières, concessions, cartographie et réglementation.",
    verbose=True,
)

architect = Agent(
    role="Architecte logiciel desktop cross-platform",
    goal="Définir une architecture robuste Tauri + React + SQLite + packaging Windows/Linux.",
    backstory="Architecte senior spécialisé en applications locales, données sensibles et UX métier.",
    verbose=True,
)

qa = Agent(
    role="Validateur QA",
    goal="Détecter les incohérences, risques, oublis fonctionnels et problèmes de testabilité.",
    backstory="Expert qualité logicielle, tests automatisés, cahiers des charges et conformité.",
    verbose=True,
)

task_spec = Task(
    description=f"""
Lis le cahier des charges ci-dessous et produis une synthèse structurée.

SPEC.md:
{spec}

Règles agents:
{agents_rules}

Livrable attendu:
- modules fonctionnels
- MVP
- V1
- V2
- critères d’acceptation
- risques
- dépendances
""",
    expected_output="Un document Markdown complet d’exigences fonctionnelles.",
    agent=product_owner,
    output_file=str(ROOT / "docs/fonctionnel/exigences.md"),
)

task_archi = Task(
    description="""
À partir des exigences fonctionnelles, propose l’architecture technique complète.

Inclure:
- structure du dépôt
- stack technique
- schéma de base SQLite
- modules applicatifs
- système de migrations
- stratégie de sauvegarde/restauration
- tests
- packaging Windows/Linux
- stratégie multi-agents
""",
    expected_output="Un document Markdown d’architecture technique.",
    agent=architect,
    context=[task_spec],
    output_file=str(ROOT / "docs/architecture/architecture-technique.md"),
)

task_qa = Task(
    description="""
Relis les livrables précédents.
Détecte les incohérences, oublis, zones floues et risques.
Produis un rapport QA actionnable.
""",
    expected_output="Un rapport QA Markdown.",
    agent=qa,
    context=[task_spec, task_archi],
    output_file=str(ROOT / "reports/qa/revue_initiale.md"),
)

crew = Crew(
    agents=[product_owner, architect, qa],
    tasks=[task_spec, task_archi, task_qa],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    result = crew.kickoff()
    print(result)
