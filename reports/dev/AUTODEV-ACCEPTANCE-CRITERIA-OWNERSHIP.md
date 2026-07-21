# AUTODEV Acceptance Criteria Ownership

## objectif

Corriger `autodev review-task` pour que l'identité d'un critère propriétaire repose uniquement sur `requirement_id` et `acceptance_criterion_id`, sans jamais comparer ni faire confiance à un texte reformulé par Codex.

## fichiers modifiés

- `autodev/src/autodev/review_task.py`
- `autodev/schemas/review-result.schema.json`
- `autodev/tests/test_acceptance_criteria.py`
- `reports/dev/AUTODEV-ACCEPTANCE-CRITERIA-OWNERSHIP.md`

## décisions prises

- Le schéma `review-result` n'exige plus `criterion` dans `requirement_checks`, mais l'accepte encore temporairement pour compatibilité.
- `review-task` valide désormais les critères propriétaires uniquement par identifiants et parenté officielle backlog.
- Les ids inconnus, dupliqués, manquants ou appartenant à une autre tâche sont rejetés explicitement.
- Le texte final du champ `criterion` est toujours réinjecté depuis le backlog officiel, même si Codex fournit un ancien format avec texte reformulé.
- Le prompt de revue interdit désormais de générer ou reformuler le texte des critères et impose la recopie exacte des ids dans l'ordre fourni.

## problèmes connus

- Le mode legacy sans `acceptance_criterion_id` reste supporté uniquement quand toute la liste `requirement_checks` est dans l'ancien format positionnel ; ce mode dépend toujours de l'ordre attendu.

## résultats des tests

- `python -m compileall -q autodev/src` : OK
- `pytest -q autodev/tests` : OK (`148 passed in 10.31s`)

## prochaine étape

Supprimer complètement le champ legacy `criterion` côté génération Codex quand tous les consommateurs internes auront migré vers l'identité par ids et la normalisation locale.
