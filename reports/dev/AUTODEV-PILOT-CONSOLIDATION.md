# AUTODEV-PILOT-CONSOLIDATION

## objectif

Consolider l'ordonnanceur `autodev` après le pilote pour rendre les prochains `run-feature` plus autonomes, reproductibles et prévisibles, sans ajouter de fonctionnalité métier et sans exécuter d'agent métier réel.

## enseignements du pilote

- Les décisions basées sur des artefacts figés (`produced_commit`, diff, chemins modifiés) sont fragiles après amend ou reprise.
- Les validations et appels externes ont besoin de timeouts homogènes et d'une gestion stricte des processus enfants.
- Les artefacts générés de test doivent être ignorés pour le scope tant qu'ils ne sont pas suivis par Git.
- Les changements de dépendances et validations trop larges doivent être explicités plutôt qu'acceptés implicitement.
- Les rapports doivent être recalculés ou vérifiés à partir de l'état Git courant avant revue.

## règles consolidées

- Tous les appels externes passent par une exécution avec timeout profilé.
- Le reviewer et l'intégrateur recalculent toujours le diff courant depuis `base_commit` vers le `HEAD` réel de la branche de tâche.
- Les artefacts générés connus sont filtrés du scope seulement s'ils ne sont pas suivis par Git.
- Un manifeste de dépendance (`package.json`, `package-lock.json`, `Cargo.lock`, `src-tauri/Cargo.toml`) requiert une justification explicite.
- Une validation large déductiblement remplaçable par un test ciblé est refusée sans justification explicite.
- Le rapport de tâche vérifié avant revue doit correspondre au diff courant et aux validations réelles.
- Une feature `COMPLETED` n'est pas rejouée ; son rapport final est régénéré de manière déterministe.

## architecture finale retenue

- `autodev.process_runner` centralise les timeouts, la capture de flux et l'arrêt du groupe de processus.
- `autodev.generated_artifacts` centralise les artefacts générés connus et les règles de reproductibilité des dépendances.
- `autodev.git_context` factorise la résolution du contexte Git courant d'une tâche.
- `autodev.task_report` impose un rapport de tâche déterministe vérifié avant revue.
- `autodev.feature_status` alimente la commande déterministe `autodev status`.

## limites restantes

- La détection des validations trop larges repose sur une heuristique volontairement simple autour des fichiers de test ciblés.
- La détection de modification de dépendances s'appuie sur les manifestes versionnés, pas sur l'intention réelle de l'agent.
- Le rapport final de feature synthétise les artefacts utiles mais ne reconstruit pas un historique détaillé minute par minute.
- Le dépôt annonce `agents/STATUS.md` comme source de vérité, mais seul `STATUS.md` de redirection est présent dans cet environnement.

## commandes de contrôle

- `python -m compileall -q autodev/src`
- `pytest -q autodev/tests`
- `autodev --help`
- `autodev status --help`
- `autodev run-feature --help`

## tests exécutés

- `pytest -q autodev/tests/test_task_runner.py autodev/tests/test_consolidation.py`
- `pytest -q autodev/tests/test_run_feature.py`
- `pytest -q autodev/tests/test_planner.py autodev/tests/test_validation_baseline.py autodev/tests/test_git_tools.py`
- Validation finale complète exécutée après les modifications.

## fichiers modifiés

- `autodev/src/autodev/`
- `autodev/tests/`
- `autodev/schemas/backlog.schema.json`
- `reports/dev/AUTODEV-PILOT-CONSOLIDATION.md`

## décisions prises

- Garder la factorisation simple et locale, sans framework d'exécution supplémentaire.
- Préférer une vérification déterministe des rapports de tâche à une tentative d'interprétation tolérante.
- Refuser les changements de dépendances non justifiés au niveau backlog pour bloquer les dépendances purement locales.
- Produire `final-report.json` et `reports/dev/FEATURE-ID.md` automatiquement à la fin d'une feature `COMPLETED`.

## problèmes connus

- L'heuristique de ciblage des validations ne couvre pas tous les outils de test possibles.
- Les timeouts marquent correctement l'état `TIMEOUT`, mais la classification détaillée par famille d'outil reste volontairement minimaliste.

## résultats des tests

Voir la validation finale exécutée sur l'arborescence `autodev/`.

## prochaine étape

Exécuter une prochaine feature autodev réelle avec `autodev status` et les nouveaux garde-fous pour vérifier le comportement bout en bout sur un backlog métier.
