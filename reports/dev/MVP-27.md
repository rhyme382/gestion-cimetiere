# MVP-27 — `autodev run-feature` avec LangGraph

**Date :** 2026-07-14  
**Agent :** orchestration  
**Statut :** ✅ Complete

## objectif

Ajouter la commande `autodev run-feature BACKLOG_JSON` pour orchestrer séquentiellement toutes les tâches d’une fonctionnalité avec LangGraph, reprise sur checkpoint SQLite, boucle de correction automatique, et tests sans exécution réelle de Claude ou Codex.

## fichiers modifiés

- `autodev/src/autodev/cli.py`
- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/correct_task.py`
- `autodev/src/autodev/run_feature.py`
- `autodev/tests/test_run_feature.py`
- `agents/reports/2026-07-14-autodev-run-feature-langgraph.md`
- `reports/dev/MVP-27.md`

## décisions prises

- Graphe LangGraph simple avec nœuds `load_backlog`, `select_next_task`, `run_task`, `review_task`, `decide_review`, `correct_task`, `integrate_task`, `finish`.
- Statuts réels déduits exclusivement depuis les artefacts `.autodev/runs/TASK-ID/integration/integration-result.json` et `.autodev/runs/TASK-ID/review/review-result.json`.
- Checkpoints stockés dans `.autodev/state/checkpoints.sqlite` avec un `thread_id` stable dérivé de `feature_id`.
- Correction automatique isolée dans `correct_task.py`, avec réutilisation du worktree existant, validations rejouées, contrôle strict des `allowed_paths` et amend du commit courant.
- Redémarrage `--resume` basé sur le dernier état checkpointé, sans rejouer les tâches déjà intégrées.

## problèmes connus

- La règle "créer une branche Git par tâche" n’a pas pu être appliquée dans cet environnement car l’écriture dans `.git/refs/heads` échoue en lecture seule.
- `agents/STATUS.md` est référencé comme source officielle mais n’existe pas actuellement dans le dépôt.
- `correct_task.py` est couvert indirectement par l’orchestrateur ; une suite unitaire dédiée à ce module serait encore utile pour renforcer la non-régression fine du flux de correction.

## résultats des tests

Commande exécutée :

```bash
pytest autodev/tests/test_run_feature.py autodev/tests/test_task_runner.py autodev/tests/test_review_task.py autodev/tests/test_integrate_task.py
```

Résultat :

- `41 passed in 1.64s`
- Aucun agent métier réel lancé pendant les tests.
- Cas couverts : sélection, dépendances, tâches déjà intégrées, verdicts `APPROVED` / `CORRECTION_REQUIRED` / `HUMAN_REVIEW_REQUIRED`, dépassement `max_corrections`, reprise checkpoint, non-rejeu des tâches intégrées, enregistrement des erreurs.

## prochaine étape

Ajouter des tests unitaires directs sur `correct_task.py`, puis exercer `autodev run-feature` sur un backlog d’intégration réaliste avec faux runners CLI pour valider aussi la couche d’affichage utilisateur.
