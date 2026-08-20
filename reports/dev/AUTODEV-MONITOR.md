# AUTODEV-MONITOR

## objectif

Ajouter une commande locale `autodev monitor BACKLOG_JSON` pour superviser en temps réel une feature autodev sans appel LLM, sans écriture dans les runs et sans action Git destructive.

## fichiers modifiés

- `autodev/src/autodev/monitor_state.py`
- `autodev/src/autodev/monitor.py`
- `autodev/src/autodev/cli.py`
- `autodev/tests/test_monitor.py`
- `reports/dev/AUTODEV-MONITOR.md`

## décisions prises

- Lecture déterministe limitée aux artefacts explicitement demandés: backlog, `last-state.json`, `run-feature-result.json`, résultats de tâche, corrections, intégration, logs et métadonnées Git locales.
- Séparation simple en deux modules:
  - `monitor_state.py` pour la lecture d’état, la dérivation des statuts, la lecture bornée des logs et l’état Git.
  - `monitor.py` pour le rendu Rich et la boucle de rafraîchissement.
- Utilisation de fonctions pures pour la lecture d’état, le calcul des statuts, le tail des logs, le modèle de rendu et le calcul d’état Git.
- Affichage de `—` quand une donnée est absente afin de rester robuste aux artefacts partiels.
- Lecture des logs en fin de fichier uniquement via une lecture par blocs inversée pour éviter de charger de gros fichiers complets en mémoire.
- Gestion propre de `Ctrl-C` via sortie silencieuse de la boucle de monitoring.

## commandes

- `autodev monitor BACKLOG_JSON`
- `autodev monitor BACKLOG_JSON --once`
- `autodev monitor BACKLOG_JSON --logs --log-lines 30`
- `autodev monitor BACKLOG_JSON --refresh 1.0 --no-clear`

## états affichés

- `PENDING`
- `READY`
- `IMPLEMENTING`
- `REVIEWING`
- `CORRECTING`
- `APPROVED`
- `INTEGRATING`
- `INTEGRATED`
- `FAILED`
- `TIMEOUT`
- `HUMAN_REVIEW_REQUIRED`
- `COMPLETED`

## sources de données

- backlog JSON
- `.autodev/runs/features/FEATURE-ID/last-state.json`
- `.autodev/runs/features/FEATURE-ID/run-feature-result.json`
- `.autodev/runs/TASK-ID/result.json`
- `.autodev/runs/TASK-ID/review/review-result.json`
- `.autodev/runs/TASK-ID/integration/integration-result.json`
- `.autodev/runs/TASK-ID/corrections/`
- branches et worktrees Git existants
- fichiers de logs existants

## limites

- Le monitor ne lance aucune action et n’essaie pas de réparer un état incohérent; il l’expose seulement.
- Les détails Git courants dépendent des artefacts déjà présents pour retrouver `base_commit` et le worktree.
- Le statut global peut afficher `NOT_STARTED` si aucun artefact d’exécution n’existe encore.

## exemples

```bash
autodev monitor .autodev/plans/concession-lifecycle.backlog.json --once
autodev monitor .autodev/plans/concession-lifecycle.backlog.json --logs
autodev monitor .autodev/plans/concession-lifecycle.backlog.json --refresh 0.5 --no-clear
```

## dépannage

- Si la commande échoue sur le backlog, vérifier le JSON et la cohérence des identifiants de tâches et dépendances.
- Si une tâche apparaît en `FAILED` avec worktree absent ou branche absente, vérifier les artefacts `.autodev/runs/TASK-ID/` et l’état Git local.
- Si aucun log n’apparaît avec `--logs`, c’est qu’aucun des fichiers de log attendus n’existe encore pour l’action courante.

## problèmes connus

- Les états d’intégration Git non listés dans l’interface demandée, comme `CONFLICT`, sont ramenés à `FAILED` dans l’état affiché tout en conservant le statut d’intégration détaillé dans la table.

## résultats des tests

- `python -m compileall -q autodev/src`
- `pytest -q autodev/tests/test_monitor.py`
- validation complète à exécuter sur `autodev/tests`

## prochaine étape

Exécuter la batterie complète demandée sur le dépôt courant puis utiliser `autodev monitor ... --once` sur un backlog réel de fixture pour vérifier le rendu terminal.
