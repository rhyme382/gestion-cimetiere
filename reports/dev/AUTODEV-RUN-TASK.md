# AUTODEV-RUN-TASK

## objectif

Fiabiliser `autodev run-task BACKLOG_JSON TASK_ID` pour que Claude Code soit lancé dans le worktree isolé avec les permissions non interactives attendues, que le prompt reste transmis via stdin et qu’un faux succès lié à une demande de permissions soit explicitement détecté.

## fichiers modifiés

- `autodev/src/autodev/task_runner.py`
- `autodev/tests/test_task_runner.py`
- `reports/dev/AUTODEV-RUN-TASK.md`

## décisions prises

- L’appel `claude -p` utilise désormais `--permission-mode bypassPermissions` et restreint explicitement les outils à `Bash,Edit,Write,Read,Glob,Grep`.
- Le prompt n’est toujours pas passé en argument CLI ; il reste transmis via `subprocess.run(..., input=prompt, text=True, capture_output=True, check=False)`.
- Le `cwd` de Claude reste le worktree isolé et `--add-dir` est supprimé car il dupliquait ce même répertoire sans apporter de garde-fou supplémentaire.
- `result.json`, `claude.stdout.log` et `claude.stderr.log` sont écrits même si Claude quitte avec un code non nul.
- Un code de sortie `0` ne suffit plus : si la sortie de Claude contient encore une demande de permissions, l’exécution est marquée en échec explicite.
- Les tests n’appellent jamais réellement `claude`; ils injectent un faux runner ou mockent `subprocess.run`.

## problèmes connus

- En cas d’échec après création de branche/worktree, l’orchestrateur conserve volontairement les artefacts pour audit ; aucun nettoyage automatique n’est encore appliqué.
- Les validations sont toujours exécutées après le contrôle Git de succès Claude ; ce correctif ne modifie pas la politique de succès/échec liée aux commandes de validation.

## résultats des tests

- `python -m compileall -q autodev/src` : OK
- `pytest -q autodev/tests` : OK, 9 tests passés

## prochaine étape

Élargir au besoin la détection de faux succès à d’autres formulations de refus de permissions si de nouveaux messages Claude apparaissent en production.
