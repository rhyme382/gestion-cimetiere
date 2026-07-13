# AUTODEV-RUN-TASK

## objectif

Fiabiliser `autodev run-task BACKLOG_JSON TASK_ID` pour que le prompt Claude soit transmis en mode non interactif via stdin, que les artefacts de run soient toujours écrits en cas d’échec Claude et que l’erreur réelle Claude remonte au lieu d’un faux diagnostic Git.

## fichiers modifiés

- `autodev/src/autodev/task_runner.py`
- `autodev/tests/test_task_runner.py`
- `reports/dev/AUTODEV-RUN-TASK.md`

## décisions prises

- L’appel `claude -p` ne reçoit plus le prompt comme argument final ; le texte complet est transmis via `subprocess.run(..., input=prompt, text=True, capture_output=True, check=False)`.
- Le `cwd` de Claude reste le worktree isolé et `--add-dir` pointe vers ce worktree pour éviter toute écriture dans le dépôt principal.
- `result.json`, `claude.stdout.log` et `claude.stderr.log` sont écrits même si Claude quitte avec un code non nul.
- Le contrôle “aucune modification / aucun commit” n’est exécuté que si Claude a quitté avec le code `0`.
- Les tests n’appellent jamais réellement `claude`; ils injectent un faux runner ou mockent `subprocess.run`.

## problèmes connus

- En cas d’échec après création de branche/worktree, l’orchestrateur conserve volontairement les artefacts pour audit ; aucun nettoyage automatique n’est encore appliqué.
- Les validations sont toujours exécutées après le contrôle Git de succès Claude ; ce correctif ne modifie pas la politique de succès/échec liée aux commandes de validation.

## résultats des tests

- `python -m compileall -q autodev/src` : OK
- `pytest -q autodev/tests` : OK, 8 tests passés
- `autodev run-task --help` : OK

## prochaine étape

Ajouter, si nécessaire, un test d’intégration contrôlé sur un vrai binaire Claude dans un environnement dédié, distinct de la suite unitaire, pour vérifier le comportement des permissions sans rendre les tests locaux dépendants de Claude.
