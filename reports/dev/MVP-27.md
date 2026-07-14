# MVP-27 — `autodev run-feature` avec LangGraph

**Date :** 2026-07-14  
**Agent :** orchestration  
**Statut :** ✅ Complete

## objectif

Ajouter la commande `autodev run-feature BACKLOG_JSON` pour orchestrer séquentiellement toutes les tâches d’une fonctionnalité avec LangGraph, reprise sur checkpoint SQLite, boucle de correction automatique, et tests sans exécution réelle de Claude ou Codex.

Correction complémentaire du 2026-07-14 : unifier la vérification des dépendances entre `run-feature` et `run-task` via les artefacts d’intégration `.autodev/runs/TASK-ID/integration/integration-result.json`.

Correction complémentaire du 2026-07-14 (reprise `--resume`) : déterminer l’étape réelle à reprendre depuis Git et les artefacts de tâche, sans jamais relancer `run-task` si une branche de tâche existe déjà.

## fichiers modifiés

- `autodev/src/autodev/cli.py`
- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/correct_task.py`
- `autodev/src/autodev/run_feature.py`
- `autodev/src/autodev/task_dependencies.py`
- `autodev/src/autodev/task_runner.py`
- `autodev/tests/test_run_feature.py`
- `autodev/tests/test_task_runner.py`
- `agents/reports/2026-07-14-autodev-run-feature-langgraph.md`
- `reports/dev/MVP-27.md`

## décisions prises

- Graphe LangGraph simple avec nœuds `load_backlog`, `select_next_task`, `run_task`, `review_task`, `decide_review`, `correct_task`, `integrate_task`, `finish`.
- Statuts réels déduits exclusivement depuis les artefacts `.autodev/runs/TASK-ID/integration/integration-result.json` et `.autodev/runs/TASK-ID/review/review-result.json`.
- La règle de dépendance est maintenant factorisée dans `task_dependencies.py` ; `run-feature` et `run-task` partagent exactement la même lecture d’artefact et n’utilisent plus `task.status` du backlog.
- Checkpoints stockés dans `.autodev/state/checkpoints.sqlite` avec un `thread_id` stable dérivé de `feature_id`.
- Correction automatique isolée dans `correct_task.py`, avec réutilisation du worktree existant, validations rejouées, contrôle strict des `allowed_paths` et amend du commit courant.
- Redémarrage `--resume` basé sur le dernier état checkpointé, sans rejouer les tâches déjà intégrées.
- La reprise de tâche passe désormais par `determine_task_resume_action(...)`, qui choisit explicitement entre `IMPLEMENT`, `REVIEW`, `CORRECT`, `INTEGRATE`, `COMPLETED`, `HUMAN_REVIEW` et `INVALID_STATE`.
- Les états incohérents détectés par Git et les artefacts (`branche sans worktree`, `worktree sans branche`, `APPROVED sans commit`, `JSON invalide`) échouent avec un message explicite sans suppression automatique.

## problèmes connus

- La règle "créer une branche Git par tâche" n’a pas pu être appliquée dans cet environnement car l’écriture dans `.git/refs/heads` échoue en lecture seule.
- `agents/STATUS.md` est référencé comme source officielle mais n’existe pas actuellement dans le dépôt.
- `correct_task.py` est couvert indirectement par l’orchestrateur ; une suite unitaire dédiée à ce module serait encore utile pour renforcer la non-régression fine du flux de correction.
- L’exécutable `autodev` n’est pas disponible dans le shell de validation ; l’aide CLI a donc été vérifiée via `PYTHONPATH=autodev/src python -m autodev.cli run-feature --help`.

## résultats des tests

Commandes exécutées :

```bash
python -m compileall -q autodev/src
pytest -q autodev/tests
autodev run-feature --help
PYTHONPATH=autodev/src python -m autodev.cli run-feature --help
```

Résultat :

- `63 passed in 2.33s`
- `python -m compileall -q autodev/src` : succès
- `autodev run-feature --help` : échec environnemental (`autodev: command not found`)
- `PYTHONPATH=autodev/src python -m autodev.cli run-feature --help` : succès
- Aucun agent métier réel lancé pendant les tests.
- Cas couverts : sélection, dépendances, tâches déjà intégrées, verdicts `APPROVED` / `CORRECTION_REQUIRED` / `HUMAN_REVIEW_REQUIRED`, dépassement `max_corrections`, reprise checkpoint, non-rejeu de `run-task` sur branche existante, enregistrement des erreurs.
- Couverture complémentaire ajoutée : nouvelle tâche `IMPLEMENT`, branche+worktree+commit sans revue `REVIEW`, verdicts menant à `CORRECT` / `INTEGRATE` / `COMPLETED`, reprise bloquée en `HUMAN_REVIEW`, reprise directe vers `review_task` sans rejeu de `run-task`, états incohérents explicites, JSON invalide, boucle correction→revue→intégration.

## prochaine étape

Ajouter des tests unitaires directs sur `correct_task.py`, puis rétablir l’installation du binaire `autodev` dans l’environnement pour pouvoir rejouer la validation CLI exacte sans contournement `python -m`.
