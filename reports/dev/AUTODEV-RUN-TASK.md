# AUTODEV-RUN-TASK

## objectif

Ajouter la commande `autodev run-task BACKLOG_JSON TASK_ID` avec un mode `--dry-run`, un worktree Git isolé, une exécution non interactive de Claude Code, des contrôles de sécurité sur les validations et une traçabilité complète des artefacts de run.

## fichiers modifiés

- `autodev/src/autodev/cli.py`
- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/task_runner.py`
- `autodev/tests/test_task_runner.py`
- `reports/dev/AUTODEV-RUN-TASK.md`

## décisions prises

- Ajout de deux modules simples seulement :
  - `git_tools.py` pour les opérations Git ciblées ;
  - `task_runner.py` pour l’orchestration `run-task`.
- Les dépendances sont considérées terminées uniquement si la tâche dépendante porte un champ optionnel `status` avec une valeur de type `completed`, `done`, `finished`, `terminated`, `terminee` ou `terminée`.
- Le prompt transmis à Claude inclut `SPEC.md`, la tâche complète, les exigences liées, les critères d’acceptation, les chemins autorisés, les commandes de validation et les interdictions demandées.
- Les commandes de validation sont exécutées sans `shell=True` et rejetées si elles contiennent des opérateurs shell composés ou redirections.
- Les tests n’appellent jamais réellement `claude` et couvrent uniquement la logique Python.

## problèmes connus

- Le schéma de backlog actuel n’expose pas explicitement un champ `status`; la vérification des dépendances repose donc sur un champ optionnel toléré par le runner mais non imposé par le schéma existant.
- En cas d’échec après création de branche/worktree, cette première version ne supprime pas automatiquement les artefacts Git déjà créés.
- La vérification des chemins autorisés s’appuie sur les chemins réellement modifiés vus par Git; elle ne remonte pas l’intention de modification si aucun changement n’a été matérialisé.

## résultats des tests

- `python -m compileall -q autodev/src` : OK
- `pytest -q autodev/tests` : OK, 6 tests passés
- `PYTHONPATH=autodev/src autodev/.venv/bin/autodev --help` : OK

## prochaine étape

Tester `run-task` sur un backlog réel avec un faux runner Claude injectable ou un environnement d’intégration contrôlé, puis décider si le schéma backlog doit formaliser le statut des tâches et si un nettoyage automatique des worktrees échoués est souhaité.
