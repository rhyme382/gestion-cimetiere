# Objectif

Corriger `autodev integrate-task` pour exécuter les validations `TASK` pré-fusion dans le worktree réel de la tâche, conserver les validations `FULL` sur la branche cible, et tracer le contexte d'exécution exact dans les artefacts.

# Fichiers modifiés

- `autodev/src/autodev/integrate_task.py`
- `autodev/src/autodev/validation_baseline.py`
- `autodev/tests/test_integrate_task.py`
- `autodev/tests/test_validation_baseline.py`
- `reports/dev/AUTODEV-INTEGRATE-TASK-WORKTREE.md`

# Décisions prises

- `TASK_PRE_MERGE` exécute désormais `task.validation_commands` avec `cwd` fixé au worktree existant de la tâche et refuse explicitement l'intégration si ce worktree est absent, non enregistré ou sale.
- `FULL_BASELINE` reste exécuté dans le dépôt principal sur la branche cible avant fusion temporaire.
- `TASK_POST_MERGE` et `FULL_POST_MERGE` restent exécutés dans le dépôt principal après fusion temporaire.
- Chaque payload `validation-results.json` et chaque résultat de commande embarquent désormais `cwd` et `execution_context` pour audit.
- Aucun agent métier réel ni dépôt métier réel n'a été utilisé dans les tests ; seuls des dépôts Git temporaires de test sont créés.

# Problèmes connus

- Le fichier racine `agents/STATUS.md` mentionné par `AGENTS.md` est toujours absent du dépôt ; ce rapport complète seulement la traçabilité locale.
- Si un worktree existe physiquement mais n'est plus enregistré par Git, l'intégration échoue avant validation, ce qui est volontairement strict.

# Résultats des tests

Commandes exécutées :

```bash
python -m compileall -q autodev/src
PYTHONPATH=autodev/src pytest -q autodev/tests
```

Résultat :

- `python -m compileall -q autodev/src` : succès
- `PYTHONPATH=autodev/src pytest -q autodev/tests` : `97 passed in 4.20s`
- Couverture ajoutée : pré-merge dans worktree uniquement, absence de worktree, refus worktree sale, contexte d'exécution et `cwd` tracés dans les artefacts

# Prochaine étape

Retester un scénario orchestré `run-feature` qui enchaîne `review-task` puis `integrate-task`, afin de vérifier que les nouveaux artefacts de contexte sont correctement consommés sans lancer d'intégration métier réelle.
