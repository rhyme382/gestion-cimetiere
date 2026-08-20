# Objectif

Ajouter la commande `autodev integrate-task BACKLOG_JSON TASK_ID` pour intégrer de façon contrôlée une tâche approuvée dans la branche courante, avec validations, artefacts et nettoyage du worktree.

Correction complémentaire du 2026-07-14 : recalculer systématiquement le diff Git courant `base_commit..HEAD` de la branche `autodev/TASK-ID`, publier les artefacts `current-diff.patch`, `current-paths.json` et `current-name-status.txt`, et ignorer tout ancien `diff.patch`, `modified_paths` ou `produced_commit` devenu obsolète après amend.

# Fichiers modifiés

- `autodev/src/autodev/cli.py`
- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/integrate_task.py`
- `autodev/tests/test_integrate_task.py`
- `reports/dev/AUTODEV-INTEGRATE-TASK.md`

# Décisions prises

- Implémentation isolée dans `autodev/src/autodev/integrate_task.py` pour préserver `doctor`, `plan`, `run-task` et `review-task`.
- Intégration contrôlée via `git merge --no-ff --no-commit` puis commit explicite `autodev integrate-task TASK-ID`.
- Rollback automatique limité au cas sûr où les validations post-intégration n’ont laissé aucune modification non commitée.
- Nettoyage du worktree uniquement après intégration réussie ; la branche de tâche est conservée.
- La source de vérité du périmètre intégré est désormais exclusivement le diff Git courant entre `base_commit` et le `HEAD` actuel de `autodev/TASK-ID`.
- Les anciens artefacts de `run-task` sont conservés pour audit, mais ne participent plus aux décisions d’intégration.

# Problèmes connus

- Si une validation post-intégration modifie le dépôt avant d’échouer, la commande passe en `HUMAN_REVIEW_REQUIRED` au lieu de forcer un rollback destructif.
- Le statut `agents/STATUS.md` n’a pas été modifié ici ; le rapport complète la traçabilité de la tâche côté développement.
- Le dépôt ne contient toujours pas `agents/STATUS.md` malgré la règle indiquée dans `AGENTS.md`.

# Résultats des tests

Commandes exécutées :

```bash
python -m compileall -q autodev/src
PYTHONPATH=autodev/src pytest -q autodev/tests
PYTHONPATH=autodev/src python -m autodev.cli integrate-task --help
```

Résultat :

- `python -m compileall -q autodev/src` : succès
- `PYTHONPATH=autodev/src pytest -q autodev/tests` : `78 passed in 3.13s`
- `PYTHONPATH=autodev/src python -m autodev.cli integrate-task --help` : succès
- Cas couverts en plus : diff obsolète contenant un fichier hors périmètre, commit amendé redevenu conforme, remplacement du `produced_commit` par le `HEAD` courant, rejet d’un hors-périmètre réellement présent dans le diff courant.

# Prochaine étape

Valider le flux complet `run-feature` avec ces nouveaux artefacts de diff courant, puis retester un `--resume` d’intégration sur un dépôt temporaire sans lancer d’intégration métier réelle.
