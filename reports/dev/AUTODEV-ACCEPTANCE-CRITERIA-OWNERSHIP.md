# AUTODEV Acceptance Criteria Ownership

## objectif

Attribuer chaque critère d'acceptation d'une exigence à une tâche propriétaire explicite afin que `review-task`, la couverture et le monitor n'évaluent que le périmètre réellement livré par la tâche.

## problème initial

L'ancien modèle rattachait les exigences entières aux tâches via `requirement_ids` et `shared_requirement_justifications`. Quand une même exigence mélangeait plusieurs livrables répartis entre plusieurs tâches, `review-task` évaluait toute l'exigence et produisait des faux refus.

## ancien modèle

- `requirements[].acceptance_criteria` était une liste de chaînes.
- L'appartenance se déduisait implicitement depuis `tasks[].requirement_ids`.
- Les exigences partagées reposaient sur `shared_requirement_justifications`, sans granularité par critère.

## nouveau modèle

Chaque critère structuré contient désormais :

- `id`
- `text`
- `owner_task_id`

La source de vérité est le propriétaire porté par chaque critère. Les listes dérivées par tâche sont calculées, non stockées.

## règles de propriété

- Tous les identifiants de critères doivent être uniques dans la feature.
- `owner_task_id` doit référencer une tâche existante.
- Une tâche propriétaire doit aussi référencer l'exigence parente dans `requirement_ids`.
- `review-task` ne reçoit que les critères propriétaires de la tâche.
- `review-result.requirement_checks` distingue `requirement_id`, `acceptance_criterion_id`, `criterion`, `status`, `evidence`.

## compatibilité

- Les anciens backlogs restent lisibles.
- Les critères legacy sont normalisés de façon déterministe.
- Si une exigence legacy n'a qu'une tâche propriétaire, les critères migrés prennent la forme `REQ-XXX-ACn`.
- Si plusieurs tâches portent une exigence legacy sans attribution exploitable, Autodev refuse avec `HUMAN_REVIEW_REQUIRED`.
- Les anciens artefacts de revue restent lisibles côté code pour ne pas casser les tests et états existants.

## migration

Une fonction déterministe `migrate_backlog_acceptance_criteria(backlog)` convertit les critères legacy en objets structurés.

Une commande CLI est ajoutée :

`autodev migrate-backlog BACKLOG_JSON --output OUTPUT_JSON`

Elle n'écrase jamais le fichier source.

## reviewer

- `run-task` n'affiche plus que les critères propriétaires de la tâche par exigence.
- `review-task` injecte le contexte parent de l'exigence sans envoyer les critères d'autres tâches.
- Le résultat de revue est validé contre l'ensemble exact des critères propriétaires attendus.

## coverage

Une matrice de couverture déterministe calcule, par critère :

- exigence parente
- identifiant du critère
- propriétaire
- état d'intégration du propriétaire
- dernier verdict
- statut du critère

Une nouvelle commande CLI est ajoutée :

`autodev coverage BACKLOG_JSON`

Options :

- `--json`
- `--once`

## monitor

Le monitor affiche maintenant :

- la couverture globale des critères dans le résumé feature ;
- le nombre de critères possédés et approuvés par tâche dans le tableau.

## exemples

Critère structuré :

```json
{
  "id": "R2-AC3",
  "text": "L'occupation incompatible d'un emplacement est refusée.",
  "owner_task_id": "T3"
}
```

Sortie `coverage` :

```text
R2
  R2-AC1  T2  APPROVED
  R2-AC2  T2  APPROVED
  R2-AC3  T3  PENDING
```

## limites

- Le schéma accepte encore l'ancien et le nouveau format pour préserver la compatibilité.
- Les anciens backlogs partagés sans ownership explicite nécessitent une migration humaine.
- La compatibilité des anciens `review-result.json` est maintenue côté lecture, mais le format cible de sortie reste le nouveau schéma enrichi.

## fichiers modifiés

- `autodev/src/autodev/acceptance_criteria.py`
- `autodev/src/autodev/planner.py`
- `autodev/src/autodev/task_runner.py`
- `autodev/src/autodev/review_task.py`
- `autodev/src/autodev/monitor_state.py`
- `autodev/src/autodev/monitor.py`
- `autodev/src/autodev/cli.py`
- `autodev/schemas/backlog.schema.json`
- `autodev/schemas/review-result.schema.json`
- `autodev/prompts/plan-feature.md`
- `autodev/tests/test_acceptance_criteria.py`

## décisions prises

- `owner_task_id` dans les critères est la source de vérité unique.
- Les ids dérivés legacy sont générés de façon stable à partir de `requirement_id` et de l'ordre des critères.
- Les exigences legacy partagées non désambiguïsables sont refusées explicitement au lieu d'inventer un propriétaire.
- La couverture se calcule localement à partir du backlog et des artefacts de revue/intégration, sans appel LLM.

## problèmes connus

- Un backlog legacy avec exigence réellement partagée entre plusieurs tâches doit être migré manuellement avant d'obtenir une propriété fine par critère.

## résultats des tests

- `python -m compileall -q autodev/src` : OK
- `pytest -q autodev/tests` : 142 passed
- `autodev coverage --help` : OK
- `autodev migrate-backlog --help` : OK
- `autodev monitor --help` : OK

## prochaine étape

Migrer progressivement les backlogs Autodev structurants vers le nouveau format `acceptance_criteria[]` avec `id` et `owner_task_id`, puis régénérer les revues futures sur ce format.
