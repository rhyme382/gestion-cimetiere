# AUTODEV-REVIEW-TASK

## objectif

Ajouter la commande `autodev review-task BACKLOG_JSON TASK_ID` pour relire une tâche développée à partir des artefacts `run-task`, exécuter Codex en lecture seule avec un schéma strict, enregistrer les artefacts de revue, et durcir la validation des `allowed_paths` pour interdire les chemins absolus et les segments `..`.

## fichiers modifiés

- `autodev/src/autodev/cli.py`
- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/path_rules.py`
- `autodev/src/autodev/planner.py`
- `autodev/src/autodev/review_task.py`
- `autodev/src/autodev/task_runner.py`
- `autodev/schemas/backlog.schema.json`
- `autodev/schemas/review-result.schema.json`
- `autodev/tests/test_review_task.py`
- `autodev/tests/test_task_runner.py`
- `reports/dev/AUTODEV-REVIEW-TASK.md`

## décisions prises

- Implémentation de `review-task` dans un module dédié pour ne pas coupler davantage `run-task` et la logique de revue.
- Réutilisation des garde-fous existants du backlog et des commandes de validation au lieu de dupliquer les règles métier.
- Normalisation centralisée des chemins backlog via `path_rules.py` pour imposer des chemins relatifs au dépôt dans `plan`, `run-task` et `review-task`.
- Appel Codex via `stdin` avec `codex exec --ephemeral --sandbox read-only --output-schema -o` afin d’éviter `shell=True` et les limites de longueur d’arguments sur les gros diffs.
- Post-vérification déterministe du verdict final pour garantir la cohérence avec les règles de scope, tests, exigences, critères et sévérités.

## problèmes connus

- La validation du résultat Codex est faite côté Python par contrôle structurel explicite ; elle complète le `--output-schema` mais n’embarque pas un moteur JSON Schema externe.
- La relance des validations protège le worktree et désactive l’écriture des `.pyc`, mais une commande tierce qui modifierait quand même le worktree ferait échouer la revue.
- Les anciens backlogs sans `specification_path` restent lisibles par `review-task` avec repli sur `SPEC.md`, mais `plan` génère désormais ce champ explicitement.

## résultats des tests

- `python -m compileall -q autodev/src`
- `pytest -q autodev/tests`
- `PYTHONPATH=autodev/src python -m autodev.cli review-task --help`

Résultat : tous les tests passent (`18 passed`), la compilation est propre et l’aide CLI de `review-task` s’affiche correctement.

## prochaine étape

Exécuter `autodev review-task` sur une tâche réelle issue de `run-task` pour valider le flux bout en bout avec un vrai binaire `codex` dans un environnement d’intégration.
