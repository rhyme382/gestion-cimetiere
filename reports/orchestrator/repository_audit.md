# Audit du dépôt

Date : 2026-06-15

## Objectif

Préparer un nettoyage du dépôt pour ne conserver dans Git que :
- le code source ;
- la documentation ;
- les prompts ;
- la configuration du projet.

Les environnements locaux, artefacts générés, journaux, états d'exécution et secrets doivent être exclus.

## Résumé de la décision

Un `.gitignore` a été ajouté pour couvrir :
- Python ;
- CrewAI ;
- Claude Code ;
- Codex CLI ;
- Node.js ;
- Tauri ;
- Rust ;
- VS Code ;
- secrets, logs et fichiers temporaires.

## Vérification des fichiers non suivis

État observé avant nettoyage :

| Chemin | Type | Décision | Motif |
| --- | --- | --- | --- |
| `.python-version` | config locale Python | Exclure | Dépend de l'environnement du poste, non nécessaire au projet |
| `.venv/` | environnement virtuel Python | Exclure | Artefact local reproductible |
| `orchestration/agents/agents.yaml` | configuration projet | Inclure | Décrit les agents de l'orchestrateur |
| `orchestration/flow.py` | code source Python | Inclure | Source exécutable du flux CrewAI |
| `orchestration/logs/orchestrator.log` | log d'exécution | Exclure | Artefact runtime |
| `orchestration/prompts/orchestrator.md` | prompt projet | Inclure | Documentation et configuration de pilotage |
| `orchestration/state/project_state.json` | état runtime | Exclure | Fichier de session local, non source |
| `orchestration/tasks/tasks.yaml` | configuration projet | Inclure | Décrit les tâches de l'orchestrateur |

## Ce qui restera visible dans Git après nettoyage

Fichiers explicitement conservés :
- `AGENTS.md`
- `CHANGELOG.md`
- `ROADMAP.md`
- `SPEC.md`
- `agents/QUEUE.md`
- `agents/STATUS.md`
- `orchestration/flow.py`
- `orchestration/agents/agents.yaml`
- `orchestration/tasks/tasks.yaml`
- `orchestration/prompts/*.md`
- `reports/orchestrator/*.md`
- `.gitignore`

## Ce qui sera exclu du dépôt

Catégories exclues :
- environnements locaux Python : `.venv/`, `venv/`, `.python-version` ;
- caches Python : `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` ;
- dépendances Node : `node_modules/` ;
- artefacts Rust/Tauri : `target/`, `src-tauri/target/` ;
- journaux : `logs/`, `*.log`, `orchestration/logs/` ;
- états locaux d'orchestration : `orchestration/state/` ;
- sorties de build : `dist/`, `build/`, `coverage/` ;
- fichiers temporaires et de sauvegarde ;
- secrets et variables d'environnement locales ;
- états locaux Claude Code et Codex CLI.

## Remarques

- `orchestration/state/project_state.json` est traité comme un état d'exécution local. Il ne doit pas être versionné tant qu'il ne devient pas une configuration métier stable.
- `orchestration/logs/orchestrator.log` est un log vide ou runtime. Il ne doit pas entrer dans l'historique Git.
- Les fichiers `orchestration/agents/agents.yaml`, `orchestration/tasks/tasks.yaml` et `orchestration/prompts/orchestrator.md` sont des éléments de configuration projet et doivent être ajoutés au dépôt lors du prochain commit de nettoyage.

## Validation effectuée

Validation de cohérence prévue via :
- revue des fichiers non suivis ;
- application du `.gitignore` ;
- contrôle final avec `git status --short`.

Aucun commit n'a été créé dans cette étape.
