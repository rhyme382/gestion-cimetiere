# Objectif

Ajouter la commande `autodev integrate-task BACKLOG_JSON TASK_ID` pour intégrer de façon contrôlée une tâche approuvée dans la branche courante, avec validations, artefacts et nettoyage du worktree.

# Fichiers modifiés

- `autodev/src/autodev/cli.py`
- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/integrate_task.py`
- `autodev/tests/test_integrate_task.py`

# Décisions prises

- Implémentation isolée dans `autodev/src/autodev/integrate_task.py` pour préserver `doctor`, `plan`, `run-task` et `review-task`.
- Intégration contrôlée via `git merge --no-ff --no-commit` puis commit explicite `autodev integrate-task TASK-ID`.
- Rollback automatique limité au cas sûr où les validations post-intégration n’ont laissé aucune modification non commitée.
- Nettoyage du worktree uniquement après intégration réussie ; la branche de tâche est conservée.

# Problèmes connus

- Si une validation post-intégration modifie le dépôt avant d’échouer, la commande passe en `HUMAN_REVIEW_REQUIRED` au lieu de forcer un rollback destructif.
- Le statut `agents/STATUS.md` n’a pas été modifié ici ; le rapport complète la traçabilité de la tâche côté développement.

# Résultats des tests

- À exécuter : `python -m compileall -q autodev/src`
- À exécuter : `pytest -q autodev/tests`
- À exécuter : `autodev integrate-task --help`

# Prochaine étape

Valider la suite complète, puis tester la commande sur un dépôt de démonstration temporaire sans intégrer la tâche réelle `TASK-PILOT-001`.
