# ORCHESTRATOR-FOUNDATION

## objectif

Construire le socle technique de l'ordonnanceur LangGraph sans lancer d'agents métier ni exécuter Codex/Claude en sous-processus pendant la mission.

## fichiers modifiés

- `orchestrator/graph/state.py`
- `orchestrator/models/task.py`
- `orchestrator/storage/task_store.py`
- `orchestrator/git/worktree_manager.py`
- `orchestrator/runners/codex_runner.py`
- `orchestrator/runners/claude_runner.py`
- `orchestrator/runners/qa_runner.py`
- `orchestrator/graph/build_graph.py`
- `orchestrator/cli.py`
- `tests/unit/orchestrator/test_task_store.py`
- `tests/unit/orchestrator/test_worktree_manager.py`
- `tests/unit/orchestrator/test_runners.py`
- `tests/unit/orchestrator/test_graph.py`
- `tests/unit/orchestrator/test_cli.py`
- `reports/dev/ORCHESTRATOR-FOUNDATION.md`
- `agents/reports/2026-07-11-orchestrator-foundation.md`

## décisions prises

- Utiliser `TypedDict` pour l'état LangGraph et `Pydantic v2` pour les contrats de tâches et de QA.
- Encapsuler Git, Codex et Claude derrière des wrappers injectables afin de tester uniquement avec des mocks.
- Limiter le graphe à un flux minimal compilable avec `LangGraph` et un checkpoint SQLite configurable.
- Stocker le backlog dans un JSON versionné avec écriture atomique via fichier temporaire + `os.replace`.
- Faire des commandes CLI en JSON pour faciliter l'automatisation inter-agents.

## problèmes connus

- Les commandes `codex exec` et `claude --print` sont des wrappers de fondation ; leur compatibilité exacte devra être validée lors de l'intégration réelle aux binaires.
- La CLI `resume` relance actuellement le même flux minimal que `run` ; la reprise sémantique fine dépendra du futur protocole de checkpoint et d'approbation.
- Le graphe ne déclenche pas encore de vrai cycle de développement ni de merge ; il prépare seulement l'ossature.

## résultats des tests

- `pytest tests/unit/orchestrator -q` → 17 tests passants
- `pytest` → 17 tests passants

## prochaine étape

Connecter ce socle au backlog réel, formaliser le schéma JSON de contrat inter-agents, puis intégrer la logique de reprise/approbation autour du checkpoint SQLite.
