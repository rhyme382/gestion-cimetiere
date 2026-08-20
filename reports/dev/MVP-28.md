# MVP-28 — correction allocation d'exigences autodev

**Date :** 2026-07-14  
**Agent :** orchestration  
**Statut :** ✅ Complete

## objectif

Corriger `autodev` pour qu'une exigence ne soit plus attribuée par défaut à plusieurs tâches, bloquer les backlogs incohérents sans justification explicite, et fournir à `review-task` les preuves des dépendances intégrées sans exiger que leurs fichiers réapparaissent dans le diff courant.

## fichiers modifiés

- `autodev/prompts/plan-feature.md`
- `autodev/schemas/backlog.schema.json`
- `autodev/src/autodev/planner.py`
- `autodev/src/autodev/review_task.py`
- `autodev/tests/test_planner.py`
- `autodev/tests/test_review_task.py`
- `autodev/tests/test_task_runner.py`
- `reports/dev/MVP-28.md`

## décisions prises

- Ajout de `shared_requirement_justifications` dans le schéma backlog pour autoriser uniquement les vrais partages d'exigence documentés explicitement.
- Validation bloquante dans `planner.py` : une exigence rattachée à plusieurs tâches est refusée si chaque tâche concernée ne fournit pas sa justification explicite.
- Validation complémentaire : une justification ne peut viser qu'une exigence connue et réellement attachée à la tâche.
- Renforcement du prompt planner : allocation 1 exigence -> 1 tâche par défaut, preuve principale sur la tâche porteuse, contributions intermédiaires décrites via `acceptance_criteria`.
- `review-task` collecte désormais les artefacts `integration-result.json`, `review-result.json` et `result.json` des dépendances intégrées pour les injecter dans le prompt comme preuves héritées.
- Le prompt de revue interdit explicitement d'exiger la réapparition des fichiers de dépendance dans le diff courant et autorise l'usage de la revue `APPROVED` + intégration comme preuve suffisante d'un livrable déjà intégré.
- Les helpers de tests génèrent désormais des exigences distinctes par défaut pour les scénarios multi-tâches ordinaires, afin d'éviter des doublons artificiels hors des tests dédiés à ce bug.

## problèmes connus

- Les backlogs existants qui dupliquent encore une même exigence sur plusieurs tâches sans justification explicite seront désormais rejetés tant qu'ils n'auront pas été corrigés ou documentés.
- Le reviewer dépend toujours de l'interprétation du prompt par l'agent de revue ; la contrainte métier est maintenant explicitée dans le contexte fourni, mais pas "forcée" par analyse sémantique locale du diff.

## résultats des tests

Commandes exécutées :

```bash
python -m compileall -q autodev/src
pytest -q autodev/tests
```

Résultat :

- `python -m compileall -q autodev/src` : succès
- `pytest -q autodev/tests` : `94 passed in 3.72s`
- Aucun agent métier réel lancé

## prochaine étape

Mettre à jour les backlogs déjà générés avant cette correction si certains réutilisent encore une même exigence sur plusieurs tâches sans `shared_requirement_justifications`.
