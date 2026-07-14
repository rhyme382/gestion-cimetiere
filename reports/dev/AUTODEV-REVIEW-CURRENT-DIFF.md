# AUTODEV-REVIEW-CURRENT-DIFF

## objectif

Fiabiliser `autodev review-task` pour que chaque revue reparte exclusivement de l’état Git actuel de la branche de tâche, même après amendement du commit produit.

## fichiers modifiés

- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/review_task.py`
- `autodev/tests/test_git_tools.py`
- `autodev/tests/test_review_task.py`
- `reports/dev/AUTODEV-REVIEW-CURRENT-DIFF.md`

## décisions prises

- `review-task` ignore désormais `run_result["produced_commit"]` comme source de vérité et résout systématiquement le commit courant via `HEAD` de la branche `autodev/TASK-ID`.
- Les données de revue recalculées à chaque lancement sont matérialisées dans `.autodev/runs/TASK-ID/review/current-diff.patch`, `current-paths.json` et `current-name-status.txt`.
- Le prompt de revue inclut désormais le `git diff --name-status` frais en plus de la liste des chemins modifiés et du diff complet.
- Les artefacts hérités de `run-task` restent conservés pour audit, mais ne sont plus utilisés pour piloter la revue.

## problèmes connus

- `review-result.json` reste contraint par son schéma existant et ne stocke pas les commits de contexte ; ces informations sont conservées dans les artefacts de revue régénérés.
- Les tests de reproduction utilisent un dépôt Git local jetable pour simuler l’amendement ; ils n’appellent toujours aucun binaire Codex réel.

## résultats des tests

- `python -m compileall -q autodev/src`
- `pytest -q autodev/tests`

## prochaine étape

Étendre le même principe de “source de vérité Git courante” aux autres étapes d’orchestration si de futurs artefacts persistent des références de commit devenues obsolètes.
