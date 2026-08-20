# AUTODEV-REVIEW-CURRENT-DIFF

## objectif

Fiabiliser `autodev review-task` pour qu’une revue reconstruise systématiquement l’état courant d’une tâche depuis `base_commit..HEAD`, relance les validations de revue et vérifie le rapport contre cette vue factuelle, même si `result.json` contient encore des métadonnées obsolètes.

## fichiers modifiés

- `autodev/src/autodev/review_task.py`
- `autodev/src/autodev/task_report.py`
- `autodev/tests/test_review_task.py`
- `reports/dev/AUTODEV-REVIEW-CURRENT-DIFF.md`

## décisions prises

- `review-task` ignore désormais `run_result["produced_commit"]` comme source de vérité et résout systématiquement le commit courant via `HEAD` de la branche `autodev/TASK-ID`.
- `review-task` relance toujours les `validation_commands` courantes pendant la revue et n’utilise plus `result.json.validations` ni `validation_summary` comme preuve.
- Les données de revue recalculées à chaque lancement sont matérialisées dans `.autodev/runs/TASK-ID/review/current-diff.patch`, `current-paths.json`, `current-name-status.txt` et `current-task-state.json`.
- Le prompt de revue inclut désormais le `git diff --name-status` frais en plus de la liste des chemins modifiés et du diff complet.
- La validation de `task-report.json` vérifie uniquement la cohérence factuelle des fichiers modifiés, validations, problèmes connus et prochaine étape au lieu d’exiger une égalité JSON stricte avec un ancien snapshot.
- Les artefacts hérités de `run-task` restent conservés pour audit, mais ne sont plus utilisés pour piloter la revue.

## problèmes connus

- `review-result.json` reste contraint par son schéma existant et ne stocke pas lui-même `base_commit` et `current_commit` ; ces informations sont conservées dans `current-task-state.json`.
- Les tests de reproduction utilisent un dépôt Git local jetable pour simuler l’amendement ; ils n’appellent toujours aucun binaire Codex réel.

## résultats des tests

- `python -m compileall -q autodev/src`
- `pytest -q autodev/tests`

## prochaine étape

Étendre le même principe de “source de vérité courante” aux autres étapes d’orchestration qui relisent encore des artefacts persistés quand un état Git ou une validation recalculée doit primer.
