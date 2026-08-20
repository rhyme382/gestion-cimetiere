# MVP-27 — `autodev run-feature` avec LangGraph

**Date :** 2026-07-14  
**Agent :** orchestration  
**Statut :** ✅ Complete

## objectif

Ajouter la commande `autodev run-feature BACKLOG_JSON` pour orchestrer séquentiellement toutes les tâches d’une fonctionnalité avec LangGraph, reprise sur checkpoint SQLite, boucle de correction automatique, et tests sans exécution réelle de Claude ou Codex.

Correction complémentaire du 2026-07-14 : unifier la vérification des dépendances entre `run-feature` et `run-task` via les artefacts d’intégration `.autodev/runs/TASK-ID/integration/integration-result.json`.

Correction complémentaire du 2026-07-14 (reprise `--resume`) : déterminer l’étape réelle à reprendre depuis Git et les artefacts de tâche, sans jamais relancer `run-task` si une branche de tâche existe déjà.

Correction complémentaire du 2026-07-14 (récupération de périmètre en correction) : restaurer automatiquement les fichiers hors `allowed_paths` touchés par `correct-task`, relancer Claude une seule fois avec un prompt strict si aucune modification autorisée ne subsiste, puis basculer proprement en `HUMAN_REVIEW_REQUIRED` après dépassement du compteur global.

Correction complémentaire du 2026-07-14 (intégration et boucle) : arrêter définitivement l’invocation courante si `integrate-task` échoue ou retourne un statut autre que `INTEGRATED`, empêcher toute relance automatique de la même intégration, et réinitialiser uniquement les garde-fous de cycle lors d’un `--resume` ultérieur.

## fichiers modifiés

- `autodev/src/autodev/cli.py`
- `autodev/src/autodev/git_tools.py`
- `autodev/src/autodev/correct_task.py`
- `autodev/src/autodev/run_feature.py`
- `autodev/src/autodev/task_dependencies.py`
- `autodev/src/autodev/task_runner.py`
- `autodev/tests/test_correct_task.py`
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
- `run-feature` valide maintenant explicitement le résultat de `integrate-task` ; un retour `FAILED` ou `HUMAN_REVIEW_REQUIRED` termine le graphe au lieu de repartir vers `select_next_task`.
- Une protection générale limite le nombre de transitions par invocation et détecte la répétition d’une même sélection `(task_id, action, last_error)` avec message explicite `Cycle de workflow détecté...`.
- Les garde-fous de cycle sont réinitialisés sur une nouvelle invocation `--resume`, ce qui autorise un vrai retest ultérieur sans rejouer `run-task` ni `review-task` quand les artefacts permettent de repartir à `INTEGRATE`.
- Les états incohérents détectés par Git et les artefacts (`branche sans worktree`, `worktree sans branche`, `APPROVED sans commit`, `JSON invalide`) échouent avec un message explicite sans suppression automatique.
- `correct_task.py` enregistre désormais `before-commit.txt`, `modified-paths.json`, `out-of-scope-paths.json`, `restored-paths.json` et `correction-result.json` pour chaque tentative de correction.
- Les restaurations Git sont ciblées fichier par fichier depuis le commit de départ de la correction, sans `git reset --hard`, sans suppression du worktree et sans toucher aux modifications préexistantes.
- Le prompt de correction inclut maintenant un bloc `PÉRIMÈTRE STRICT`, la liste des tâches suivantes du backlog et un message explicite indiquant qu’elles seront exécutées séparément.
- Si une tentative ne laisse aucune modification autorisée après restauration, `correct_task` relance Claude exactement une fois avec un prompt renforcé listant les fichiers restaurés.

## problèmes connus

- La règle "créer une branche Git par tâche" n’a pas pu être appliquée dans cet environnement car l’écriture dans `.git/refs/heads` échoue en lecture seule.
- `agents/STATUS.md` est référencé comme source officielle mais n’existe pas actuellement dans le dépôt.
- `correct_task.py` est couvert indirectement par l’orchestrateur ; une suite unitaire dédiée à ce module serait encore utile pour renforcer la non-régression fine du flux de correction.
- La récupération protège les chemins nouvellement modifiés pendant la correction en cours ; si un fichier hors périmètre était déjà sale avant la correction, il n’est pas restauré automatiquement pour éviter d’écraser un état antérieur.

## résultats des tests

Commandes exécutées :

```bash
python -m compileall -q autodev/src
pytest -q autodev/tests
autodev run-feature --help
```

Résultat :

- `71 passed in 2.81s`
- `python -m compileall -q autodev/src` : succès
- `pytest -q autodev/tests/test_correct_task.py` : `8 passed in 0.76s`
- `PYTHONPATH=autodev/src pytest -q autodev/tests` : `78 passed in 3.13s`
- `autodev run-feature --help` : succès
- `PYTHONPATH=autodev/src python -m autodev.cli run-feature --help` : succès
- `PYTHONPATH=autodev/src python -m autodev.cli integrate-task --help` : succès
- Aucun agent métier réel lancé pendant les tests.
- Cas couverts : sélection, dépendances, tâches déjà intégrées, verdicts `APPROVED` / `CORRECTION_REQUIRED` / `HUMAN_REVIEW_REQUIRED`, dépassement `max_corrections`, reprise checkpoint, non-rejeu de `run-task` sur branche existante, enregistrement des erreurs.
- Couverture complémentaire ajoutée : correction strictement dans le périmètre, mélange autorisé/hors périmètre, restauration sélective, conservation des changements autorisés, absence de `git reset --hard`, re-prompt après restauration, rejet/acceptation de `package.json` selon `allowed_paths`, remontée `HUMAN_REVIEW_REQUIRED` après épuisement du compteur.
- Couverture complémentaire ajoutée : arrêt immédiat après échec d’intégration, unicité d’appel de `integrate-task` par invocation, reprise `--resume` qui retente l’intégration dans une nouvelle invocation, et détection du cycle de sélection répété.

## prochaine étape

Renforcer encore la reprise en présence d’un worktree déjà sale avant correction si ce cas devient supporté explicitement par le workflow, en conservant la garantie de ne jamais écraser des modifications antérieures.
