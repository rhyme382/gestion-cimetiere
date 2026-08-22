# AUTODEV-PRODUCT-SUPERVISOR-T08

## Objectif

Corriger les défauts bloquants AC-R7-2 et AC-R7-6 : le diagnostic de production collecte désormais toutes les preuves techniques fraîches avant chaque construction et ne propose que des actions canoniques T07, validées par le moteur de politique réel sans exécution, y compris le repli `REQUEST_HUMAN`.

## Fichiers modifiés

- `autodev/src/autodev/product_diagnostic.py`
- `autodev/schemas/product-diagnostic.schema.json`
- `autodev/tests/test_product_diagnostic.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T08.md`

## Décisions prises

- `DiagnosticBuilder` n'accepte plus de `DiagnosticFacts`. Son unique chemin de production reçoit un `EvidenceCollector` et un `ProductPolicyEngine` concrets.
- `build()` appelle systématiquement l'API publique `EvidenceCollector.collect()` juste avant de calculer le diagnostic ; aucun fait constructeur ou cache n'existe dans ce chemin.
- Les lecteurs injectables obligatoires sont : commit de base, commit courant, chemins modifiés/diff, verdict de revue, validations, état Git, corrections, incidents, décisions acquises et contexte structuré T07. Une source manquante, invalide ou en erreur bloque le diagnostic.
- Les preuves techniques (notamment validations et revue) sont conservées comme faits autoritatifs ; un récit dans les corrections ne les remplace pas.
- `ProposedAction.action_id` est un identifiant T07 fermé. Les libellés locaux historiques ne sont pas traduits implicitement et sont refusés.
- Toute proposition finale passe par un chemin unique : résolution de l'action dans le registre fermé, validation des entrées structurées contre sa définition canonique, puis appel à l'API publique T07 `ProductPolicyEngine.authorize_action(action_id, ActionExecutionContext, inputs)`.
- Une demande directe de `REQUEST_HUMAN` est transformée en dossier canonique complet puis validée par T07. Après le refus d'une action initiale, le même dossier contient les faits frais, preuves techniques, décisions à préserver, tentative refusée et choix proposés ; `REQUEST_HUMAN` est de nouveau résolu, validé et explicitement autorisé avant publication.
- Un refus, une entrée invalide, une action inconnue ou une erreur T07 concernant `REQUEST_HUMAN` lève `ProductDiagnosticError` et interrompt le build : aucun diagnostic ne contient une action non autorisée. T08 n'exécute aucune action ni commande shell et ne modifie jamais un verdict reviewer.

## Matrice critères → preuves → tests

| Critère | Preuves mises en œuvre | Tests |
|---|---|---|
| AC-R7-1 | Lecteurs typés pour commits, diff, Git, validations, revue, corrections, incidents et décisions | `test_build_collects_on_every_invocation_and_observes_commit_diff_and_validations`, `test_build_observes_review_change_and_technical_evidence_beats_narrative_report` |
| AC-R7-2 | `collect()` refuse les lecteurs absents/invalides et `build()` recollecte avant chaque diagnostic | `test_collect_without_required_readers_fails`, `test_build_calls_collect_on_every_invocation`, `test_source_error_is_forwarded_without_diagnostic` |
| AC-R7-3 | Schéma 2.0.0 : faits, inférences, contraintes, proposition canonique et confiance | `test_diagnostic_serializes_and_validates_against_schema` |
| AC-R7-4 | Le verdict de revue est une preuve lue, jamais modifiée par le builder | `test_build_observes_review_change_and_technical_evidence_beats_narrative_report` |
| AC-R7-5 | Proposition structurée uniquement, rejet des métacaractères shell, aucune exécution dans T08 | `test_proposed_action_does_not_accept_shell_steps` |
| AC-R7-6 | Chemin unique registre → validation des entrées → `ProductPolicyEngine.authorize_action`; dossier `REQUEST_HUMAN` canonique, complet et réautorisé après tout refus | `test_authorized_action_is_published_only_after_its_public_policy_validation`, `test_refused_action_authorizes_request_human_as_the_second_and_final_action`, `test_refused_action_does_not_publish_diagnostic_when_request_human_is_refused`, `test_direct_request_human_requires_one_public_policy_validation`, `test_policy_engine_error_during_fallback_stops_build_without_executor`, `test_diagnostic_authorization_never_executes_an_action` |

## Problèmes connus

- Les lecteurs autoritatifs sont des interfaces injectées : leur branchement aux producteurs T10/T11 reste volontairement hors du périmètre T08.
- Les fichiers diagnostiques issus de l'ancien vocabulaire local ne sont pas acceptés par le parcours de production ; une migration explicite devra être conçue séparément si nécessaire.

## Résultats des tests

- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_diagnostic.py -q` : 19 tests passés.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests -q` : 703 tests passés, 6 ignorés.
- `git diff --check` : passé sans sortie.

## Prochaine étape

Brancher les lecteurs injectables aux producteurs de preuves autoritatives propriétaires lorsqu'ils seront disponibles, sans assouplir l'obligation de collecte fraîche ni l'autorisation T07 de l'action finale.
