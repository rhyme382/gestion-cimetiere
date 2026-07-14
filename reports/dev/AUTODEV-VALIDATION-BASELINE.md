## objectif

Ajouter une baseline de validation différentielle dans `autodev` pour distinguer les échecs préexistants, les nouvelles régressions, les améliorations et les erreurs d'environnement pendant `integrate-task`.

## fichiers modifiés

- `autodev/config/quality-gates.yaml`
- `autodev/pyproject.toml`
- `autodev/src/autodev/integrate_task.py`
- `autodev/src/autodev/validation_baseline.py`
- `autodev/tests/test_integrate_task.py`
- `autodev/tests/test_validation_baseline.py`
- `reports/dev/AUTODEV-VALIDATION-BASELINE.md`

## décisions prises

- Introduire un module simple `validation_baseline.py` au lieu d'un framework générique.
- Exécuter les validations FULL avant et après la fusion temporaire avec artefacts dédiés sous `.autodev/runs/TASK-ID/integration/`.
- Garder les validations TASK distinctes et bloquantes avant et après fusion.
- Classer `Cannot find module ...` comme `MISSING_DEPENDENCY` et le traiter comme un échec comparable, pas comme une erreur d'environnement bloquante.
- Reporter `TOOL_MISSING`, `CONFIGURATION_ERROR` et erreurs d'exécution système comme `HUMAN_REVIEW_REQUIRED` via `ENVIRONMENT_ERROR`.

## problèmes connus

- Le parsing des signatures de tests reste volontairement heuristique et optimisé pour les sorties textuelles les plus courantes.
- Le niveau `smoke` est configuré mais n'est pas encore exploité par `integrate-task`.

## résultats des tests

- `python -m pytest autodev/tests/test_validation_baseline.py autodev/tests/test_integrate_task.py` : 25 tests passés.
- `python -m pytest autodev/tests` : 90 tests passés.

## prochaine étape

Étendre le planner pour générer automatiquement des validations TASK ciblées quand le backlog fournit des suites ou fichiers de test plus précis.
