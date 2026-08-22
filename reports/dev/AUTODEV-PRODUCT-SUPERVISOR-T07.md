# Rapport de Correction — AUTODEV-PRODUCT-SUPERVISOR-T07

## Tâche
Ajouter le moteur de politique déterministe et le registre fermé des actions

## Verdict
✅ **CORRIGÉ** — Tous les problèmes bloquants et majeurs ont été adressés

## Problèmes bloquants corrigés

### 1. Schéma de versioning (AC-R12-1)
**Problème** : Le schema_version était `"1.0"` au lieu du SemVer requis `x.y.z`
**Correction** :
- Tous les schéma_version passent de `"1.0"` à `"1.0.0"` dans:
  - Registre fermé des actions (CLOSED_ACTION_REGISTRY)
  - ProductActionRegistry.to_dict()
  - Tests unitaires correspondants

**Fichiers** : product_actions.py, test_product_policy.py

### 2. INTEGRATE_FEATURE sans baseline (AC-R9-4, AC-R12-4)
**Problème** : `INTEGRATE_FEATURE` ne protégeait pas la baseline produit
**Correction** :
- Ajout de `baseline_established` comme précondition requise
- Cela empêche l'intégration sans baseline établie
- Tests ajoutés pour vérifier le refus sans baseline et l'acceptation avec baseline

**Fichiers** : product_actions.py, test_product_policy.py

### 3. Escalade scope/ownership sans autorisation (AC-R15-2)
**Problème** : L'absence d'autorisation explicite pour scope extension ou criterion reallocation ne forçait pas `REQUEST_HUMAN`
**Correction** :
- Ajout de la méthode `_check_mandatory_escalation()` dans ProductPolicyEngine
- Implémentation de la logique qui force `REQUEST_HUMAN` quand:
  - Scope extension nécessaire mais non autorisée par politique
  - Criterion reallocation nécessaire mais non autorisée par politique
- Tests complets couvrant ces deux cas

**Fichiers** : product_policy.py, test_product_policy.py

## Problèmes majeurs corrigés

### 4. Dossiers structurés (AC-R15-3, AC-R15-8)
**Problème** : Les demandes de scope, ownership et escalade humaine n'exigeaient pas les champs minimaux
**Correction** :

#### REQUEST_SCOPE_EXTENSION
Entrées requises ajoutées:
- `file_path` — Exact file/criterion requiring extension
- `justification` — Precise reason for necessity
- `baseline_proof` — Evidence of issue from baseline
- `impact_estimate` — Estimated impact of change
- `alternatives_discarded` — Why alternatives weren't feasible
- `constraints_to_preserve` — Critical constraints to preserve

#### REQUEST_CRITERION_REALLOCATION
Entrées requises ajoutées:
- `criterion` — Exact criterion requiring reallocation
- `current_owner` — Current owner scope and constraints
- `proposed_owner` — Proposed owner capabilities
- `infeasibility_proof` — Evidence of non-feasibility
- `proposed_owner_justification` — Capability proof
- `alternatives_considered` — Why others not suitable
- `dependency_impact` — Affected dependencies

#### REQUEST_HUMAN
Entrées requises ajoutées:
- `reason` — Specific escalation reason
- `facts` — Current system state facts
- `evidence` — Audit trail and proof
- `decisions_to_preserve` — Prior decisions to preserve
- `attempted_solutions` — Tried solutions and failures
- `possible_choices` — Valid options for decision

**Fichiers** : product_actions.py

### 5. Plafonds supervisés distincts (AC-R15-7, R10)
**Problème** : Aucune distinction entre plafond ordinaire et plafond supervisé absolu
**Correction** :
- Ajout de `max_ordinary_corrections` (défaut: 3) dans ProductPolicy
- Ajout de `max_supervised_corrections` (défaut: 7) dans ProductPolicy
- Seul le dépassement du plafond supervisé absolu déclenche `REQUEST_HUMAN`
- Métadonnées de politique mise à jour (serialization, deserialization)
- Tests couvrant les deux limites distinctes

**Fichiers** : product_policy.py, test_product_policy.py

### 6. Arrêts humains obligatoires additionnels (AC-R15-6)
**Problème** : Plusieurs conditions obligatoires d'escalade n'étaient pas implémentées
**Correction** :
- Ajout de PolicyFacts pour couvrir:
  - `specification_absent` — Spécification manquante
  - `specification_generation_allowed` — Autorisation de génération
  - `incident_environment_persistent` — Incident environnemental persistant
  - `supervised_correction_limit_exceeded` — Limite supervisée dépassée
- Implémentation des cas dans `_check_mandatory_escalation()`
- Tests unitaires pour chaque cas

**Fichiers** : product_policy.py, test_product_policy.py

## Résumé des corrections

| Critère | Statut |
|---------|--------|
| AC-R12-1 | ✅ |
| AC-R12-2 | ✅ |
| AC-R12-3 | ✅ |
| AC-R12-4 | ✅ |
| AC-R15-1 | ✅ |
| AC-R15-2 | ✅ |
| AC-R15-3 | ✅ |
| AC-R15-4 | ✅ |
| AC-R15-5 | ✅ |
| AC-R15-6 | ✅ |
| AC-R15-7 | ✅ |
| AC-R15-8 | ✅ |
| R9 AC-1 | ✅ |
| R9 AC-2 | ✅ |
| R9 AC-3 | ✅ |
| R9 AC-4 | ✅ |

## Corrections finales du verdict Codex

Le verdict Codex a identifié trois problèmes majeurs supplémentaires après les corrections initiales. Ils ont tous été résolus:

### 7. REQUEST_CRITERION_REALLOCATION manquait de dossier complet (AC-R15-3)
**Problème** : Le dossier structuré manquait de trois éléments exigés par AC-R15-3:
- `baseline_proof` — Preuve de l'état de baseline
- `impact_expected` — Impact attendu de la réattribution
- `constraints_to_preserve` — Contraintes critiques à préserver

**Correction** :
- Ajout de trois `InputParameter` requis à `REQUEST_CRITERION_REALLOCATION`
- Mise à jour de `expected_effect` pour décrire le dossier complet
- Mise à jour de `audit_trail.mandatory_evidence` pour inclure les trois nouveaux champs
- Test amélioré pour vérifier la présence de tous les trois champs

**Fichiers** : product_actions.py, test_product_policy.py

### 8. APPLY_CRITERION_REALLOCATION sans garde-fou pour ambiguïté (AC-R15-4, AC-R15-5)
**Problème** : L'action pouvait être exécutée malgré une ambiguïté fonctionnelle ou un changement non-unique

**Correction** :
- Ajout de `"ambiguous_functional_impact"` en `forbidden_state` de `APPLY_CRITERION_REALLOCATION`
- Ajout de deux nouvelles `StopReason`:
  - "Reallocation would have ambiguous functional impact or affect multiple entities"
  - "Multiple reasonable owners could implement this criterion"
- Nouveau test `test_ambiguous_functional_impact_blocks_criterion_reallocation` confirmant que l'ambiguïté bloque l'action

**Fichiers** : product_actions.py, test_product_policy.py

### 9. Moteur sans contrôle explicite du scope et des plafonds (AC-R9-2)
**Problème** : `_evaluate_action()` ne contrôlait pas explicitement le scope de l'action ni les plafonds de politique

**Correction** :
- Ajout de `_check_scope_constraints()` pour vérifier que le scope de l'action respecte ses limites
- Ajout de `_check_policy_limits()` pour vérifier que les actions sensibles respectent les plafonds de politique
- Intégration de ces contrôles dans `_evaluate_action()` avant le retour final
- Nouvelle classe de tests `TestScopeAndPolicyLimits` avec 5 tests couvrant:
  - Vérification que tous les actions ont des contraintes de scope
  - Refus de scope extension quand non autorisée
  - Refus de criterion reallocation quand non autorisée
  - Refus de APPLY_SCOPE_EXTENSION sans autorisation de politique
  - Refus de APPLY_CRITERION_REALLOCATION sans autorisation de politique

**Fichiers** : product_policy.py, test_product_policy.py

## Corrections supplémentaires (verdict Codex final)

### 10. Registre non fermé et mutable (AC-R12-1)
**Problème** : Le registre pouvait être remplacé ou étendu arbitrairement sans contrôle d'unicité ni immutabilité
**Correction** :
- Conversion de `self.actions` en propriété immuable via `self._actions = tuple(actions)`
- Validation que toute instanciation personnalisée ne contient que des actions du registre canonique
- Rejet des doublons dans le registre personnalisé
- Nouvelle classe `TestRegistryImmutability` avec 4 tests:
  - Vérification que le registre global utilise exactement les 14 actions définies
  - Rejet des actions inconnues
  - Rejet des doublons
  - Vérification que la liste retournée est immuable (tuple)

**Fichiers** : product_actions.py, test_product_policy.py

### 11. Escalades obligatoires incomplètes (AC-R15-1, AC-R15-5)
**Problème** : Les cas de conflits Git, ambiguïtés métier, choix multiples et sûreté Git n'étaient pas traités
**Correction** :
- Ajout de quatre nouveaux faits à PolicyFacts:
  - `merge_conflicts_unresolved` — Conflits Git non résolus
  - `business_ambiguity_unresolved` — Ambiguïté fonctionnelle/métier
  - `git_safety_unguaranteed` — Sûreté Git impossible à garantir
  - `multiple_reasonable_solutions` — Plusieurs solutions raisonnables possibles
- Amélioration de `_check_mandatory_escalation()` pour traiter ces quatre cas avec priorité absolue
- Nouvelle classe `TestGlobalMandatoryEscalations` avec 4 tests validant chaque cas

**Fichiers** : product_policy.py, test_product_policy.py

### 12. Exécuteur typé insuffisamment strict (AC-R9-3)
**Problème** : L'exécuteur acceptait les paramètres supplémentaires et les types inconnus
**Correction** :
- Rejet des paramètres supplémentaires dans `validate_inputs()` avec liste complète des autorisés
- Rejet des types inconnus (au lieu de `return True`) dans `_type_matches()`
- Correction de la validation de types pour rejeter les booléens comme entiers
- Nouvelle classe `TestTypedExecutorStrictness` avec 3 tests:
  - Rejet des paramètres supplémentaires
  - Rejet des booléens passés comme entiers
  - Rejet des types inconnus

**Fichiers** : product_policy.py, test_product_policy.py

### 13. Contrôles de scope et plafonds incomplets (AC-R9-2)
**Problème** : Les contrôles ne vérifiaient que les métadonnées, pas les données d'exécution réelles
**Correction** :
- Ajout de classe `ExecutionContext` pour représenter les données réelles:
  - `ordinary_corrections_used` — Compteur de corrections ordinaires
  - `supervised_corrections_used` — Compteur de corrections supervisées
  - `entities_modified` — Nombre d'entités réellement modifiées
  - `modifications_audited` — Preuves d'audit présentes
  - `modification_is_mechanical` — Changement mécanique/automatisé
- Amélioration de `ProductPolicyEngine.select_action()` pour accepter un contexte d'exécution
- Amélioration de `_check_policy_limits()` pour valider les compteurs et le caractère mécanique
- Stockage du contexte d'exécution dans l'instance du moteur

**Fichiers** : product_policy.py

## Tests exécutés
```bash
env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_policy.py -q
```

Résultat: **60 passed in 0.13s** ✅

Le nombre de tests est passé de 49 à 60 en raison de:
- 4 tests pour TestGlobalMandatoryEscalations
- 3 tests pour TestTypedExecutorStrictness
- 4 tests pour TestRegistryImmutability

## Fichiers modifiés
- autodev/src/autodev/product_actions.py
- autodev/src/autodev/product_policy.py
- autodev/tests/test_product_policy.py

## Conformité finale
Tous les critères d'acceptation de tâche satisfaits avec les quatre problèmes bloquants/majeurs identifiés par le verdict Codex:
- ✅ AC-R12-1 : Registre fermé immuable contre manipulation arbitraire
- ✅ AC-R15-1/AC-R15-5 : Escalades obligatoires pour conflits Git, ambiguïtés, sûreté Git, choix multiples
- ✅ AC-R9-3 : Exécuteur strictement typé qui rejette paramètres inconnus et types invalides
- ✅ AC-R9-2 : Contrôles de scope/plafonds basés sur données d'exécution réelles, pas métadonnées

---

## Correctif après verdict `CORRECTION_REQUIRED`

### Objectif

Fermer le catalogue d'actions, transformer les exigences R9/R12/R15 en
refus bloquants et fournir une unique exécution typée, contrôlée et auditable.

### Fichiers modifiés

- `autodev/src/autodev/product_actions.py`
- `autodev/src/autodev/product_policy.py`
- `autodev/schemas/product-action.schema.json`
- `autodev/tests/test_product_policy.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T07.md`

### Décisions prises

- Les définitions canoniques sont un tuple, leurs collections internes sont
  converties en tuples, et l'index exposé est un `MappingProxyType`.
- Un registre fourni ne peut contenir que la séquence exacte des mêmes objets
  canoniques ; un identifiant connu avec une définition falsifiée est refusé.
- Le schéma ferme `action_id` par enum et un test vérifie son égalité avec le
  registre.
- `TypedActionExecutor.execute(action_id, inputs, context)` est l'unique
  chemin d'exécution : il résout l'action canonique, valide les entrées,
  applique une décision bloquante, puis distribue vers une table de handlers
  construite et figée à l'initialisation.
- Les limites ordinaires refusent et structurent le transfert au superviseur,
  sans sélectionner `REQUEST_HUMAN`; seule la limite supervisée absolue le
  sélectionne (AC-R15-7).

### Problèmes connus

Aucun problème connu dans les chemins T07. Les handlers par défaut sont des
placeholders sûrs et typés ; une intégration métier les injecte uniquement à
l'initialisation de l'exécuteur.

### Matrice critère → tests

| Critère propriétaire | Tests |
| --- | --- |
| R9 — scope, audit, mécanique, intégration | `TestBlockingPolicyMatrix::test_each_scope_extension_gate_blocks_execution`, `test_each_criterion_reallocation_gate_blocks_execution`, `test_each_integration_gate_blocks_execution` |
| R9 — exécution typée sans commande libre | `TestClosedActionExecution::test_execute_rejects_forged_action_and_free_command_or_strategy` |
| R12 — registre fermé et désérialisation fermée | `TestClosedRegistryRegression::test_registry_index_mutation_fails_and_resolution_stays_canonical`, `test_registry_rejects_external_definition_with_known_identifier`, `test_schema_ids_match_canonical_registry`, `test_syntactically_valid_unregistered_action_is_rejected` |
| R15 — décision plan explicite, ambiguïté, baseline et bornage | les deux matrices `APPLY_*` ci-dessus |
| R15-7 — limites ordinaire/supervisée | `TestBlockingPolicyMatrix::test_ordinary_limit_blocks_without_requesting_human_but_supervised_limit_escalates` |
| R15 — escalade humaine existante | `TestMandatoryEscalationToHuman`, `TestGlobalMandatoryEscalations` |

### Résultats des tests

- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_policy.py -q` : 90 passed.
- La suite complète et `git diff --check` sont rejoués avant livraison.

### Prochaine étape

Faire valider le correctif par le superviseur produit, sans commit créé dans
ce worktree conformément à la consigne.

---

## Correctif final — contexte d'exécution de `select_action()`

### Objectif

Garantir que le chemin public `select_action()` transmet le véritable
`ExecutionContext` à l'escalade obligatoire et sélectionne systématiquement
`REQUEST_HUMAN` lorsque le plafond de corrections supervisées est atteint ou
dépassé, sans faire de même pour le plafond ordinaire seul (AC-R15-7).

### Fichiers modifiés

- `autodev/src/autodev/product_policy.py`
- `autodev/tests/test_product_policy.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T07.md`

### Décisions prises

- `select_action()` passe le contexte effectif à `_check_mandatory_escalation()`.
- Le plafond supervisé est inclusif (`>=`), conformément à la convention
  « atteint ou dépassé ».
- La clé de mémoïsation inclut désormais un hash déterministe du contexte
  d'exécution, afin qu'une sélection mise en cache ne masque jamais une
  escalade ultérieure avec les mêmes faits, décisions et politique.
- Les justifications d'escalade et les preuves déjà portées par les hashes des
  faits, décisions et politique sont conservées sans modification. Le plafond
  ordinaire reste hors du chemin d'escalade obligatoire.

### Problèmes connus

Aucun problème connu dans le périmètre T07.

### Résultats des tests

Les tests publics ajoutés couvrent le budget supervisé disponible, le plafond
supervisé atteint ou dépassé, le plafond ordinaire seul, la transmission
exacte du contexte, l'isolation du cache par contexte et une escalade R15
existante.

- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_policy.py -q` : 100 passed.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests -q` : 645 passed, 6 skipped.
- `git diff --check` : succès, sans erreur de whitespace.

### Prochaine étape

Remettre le correctif sans créer de commit, conformément à la consigne.

---

## Correctif de revue — AC-R9-3, AC-R12-4, AC-R15-6

### Objectif

Supprimer l’injection publique de handlers, rendre `PRESERVE_PARTIAL_CHANGES`
strictement non destructif et faire prévaloir l’escalade humaine quand une
spécification est absente sans autorisation effective de génération.

### Fichiers modifiés

- `autodev/src/autodev/product_actions.py`
- `autodev/src/autodev/product_policy.py`
- `autodev/tests/test_product_policy.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T07.md`

### Décisions prises

- `PRESERVE_PARTIAL_CHANGES` ne peut écrire que dans
  `.autodev/backups/`, avec création exclusive. Une cible existante n’est
  reconnue idempotente que si son manifeste JSON structuré prouve l’origine
  Autodev, l’action, le chemin source et les deux empreintes de contenu ; elle
  est alors renvoyée sans écriture. Toute autre cible existante est refusée.
- La politique de génération est autorisante uniquement pour `draft` ou
  `autonomous`, et seulement avec le fait explicite
  `specification_generation_allowed=True`. Les valeurs absentes, fausses,
  inconnues et `approved[_-]only` demandent `REQUEST_HUMAN`.
- `TypedActionExecutor` n’accepte plus `handlers`. Sa table immuable est bâtie
  exclusivement depuis les identifiants canoniques et des méthodes internes
  préimplémentées ; une couverture incomplète du registre échoue à
  l’initialisation.

### Problèmes connus

Aucun dans le périmètre T07. Les sauvegardes de répertoires ne sont pas
acceptées : la préservation est volontairement bornée à un fichier régulier
afin d’éviter toute copie ou cible ambiguë.

### Matrice critère → tests

| Critère propriétaire | Chemin public vérifié | Tests |
| --- | --- | --- |
| AC-R9-1 | sélection et exécution bornées | `TestBlockingPolicyMatrix`, `TestClosedActionExecution` |
| AC-R9-2 | contrôles de scope/plafonds en exécution | `TestScopeAndPolicyLimits`, `TestBlockingPolicyMatrix` |
| AC-R9-3 | `TypedActionExecutor.execute()` et table fermée | `TestClosedActionExecution` |
| AC-R9-4 | intégration avec baseline et changements utilisateur | `TestBlockingPolicyMatrix` |
| AC-R12-1 | registre et schéma fermés | `TestClosedRegistryRegression`, `TestRegistryImmutability` |
| AC-R12-2 | validations de définition et sérialisation | `TestActionRegistry`, `TestActionSerialization`, `TestSchemaversionCompliance` |
| AC-R12-3 | contraintes de scope/audit | `TestScopeAndPolicyLimits`, `TestBlockingPolicyMatrix` |
| AC-R12-4 | sauvegarde non destructive idempotente | `TestPreservePartialChanges` |
| AC-R15-1 à AC-R15-5 | décisions, ambiguïtés et dossiers | `TestMandatoryEscalationToHuman`, `TestGlobalMandatoryEscalations`, `TestBlockingPolicyMatrix` |
| AC-R15-6 | absence de spécification et incidents | `TestMandatoryEscalationToHuman` |
| AC-R15-7 | plafonds supervisés | `TestMandatoryEscalationToHuman`, `TestBlockingPolicyMatrix` |
| AC-R15-8 | preuves d’escalade structurées | `TestStructuredDossiers`, `TestMandatoryEscalationToHuman` |

### Résultats des tests

- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_policy.py -q` :
  117 passed.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests -q` :
  662 passed, 6 skipped.
- `git diff --check` : succès, sans erreur de whitespace.

### Prochaine étape

Remettre le correctif de revue sans créer de commit.

---

## Correctif bloquant — AC-R9-2 : sélection et exécution cohérentes

### Objectif

Empêcher `select_action()` d’autoriser prématurément
`APPLY_SCOPE_EXTENSION` ou `APPLY_CRITERION_REALLOCATION`. La sélection
doit exiger les mêmes preuves d’autorisation et d’exécution que le chemin
public `execute()`.

### Fichiers modifiés

- `autodev/src/autodev/product_policy.py`
- `autodev/tests/test_product_policy.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T07.md`

### Décisions prises

- `select_action()` résout chaque action via le registre canonique, puis
  délègue les candidats à `authorize_action()`, la porte canonique également
  appelée par `TypedActionExecutor.execute()`.
- Les actions sensibles exigent maintenant des entrées effectives, un contexte
  d’exécution structuré, une politique explicite, baseline/audit, caractère
  mécanique, une seule modification bornée, périmètre respecté et absence
  d’ambiguïté. Toute porte manquante produit `REQUEST_HUMAN` avec la raison
  structurée et `authorization_allowed=False`.
- Une décision acquise doit correspondre au type et à l’identifiant de l’action,
  à l’`approval_id`, ainsi qu’au feature, à la tâche, à la cible et à la
  modification du contexte réel. Les champs métier de l’action sont aussi
  comparés exactement (`change_definition`, ou `criterion` et `new_owner`).
- `_check_policy_limits()` reçoit le contexte effectif et retourne désormais un
  refus pour les plafonds, l’audit ou le caractère mécanique absents/faux ; ces
  contraintes ne sont plus de simples justifications.
- La clé de cache comprend les faits, décisions, politique, contexte
  d’exécution et le hash des entrées candidates. Une décision valable ne peut
  donc pas être réemployée dans un autre contexte ou avec d’autres entrées.
- Le plafond supervisé garde l’escalade obligatoire ; le plafond ordinaire
  conserve son refus sans escalade humaine automatique.

### Problèmes connus

Aucun dans le périmètre T07. Les actions non sensibles conservent leur
sélection de recommandation sans entrées candidates fabriquées ; les portes
d’exécution sont toujours appliquées lorsqu’elles sont effectivement exécutées.

### Matrice critère → tests

| Critère propriétaire | Chemin public vérifié | Tests |
| --- | --- | --- |
| AC-R9-2 | sélection sensible sans décision ou preuve | `TestPublicSensitiveActionSelection::test_sensitive_action_is_refused_without_acquired_decision`, `test_sensitive_action_is_refused_for_each_runtime_gate` |
| AC-R9-2 | identité exacte de la décision acquise et définition alignée sur le contexte | `TestPublicSensitiveActionSelection::test_sensitive_action_is_refused_when_decision_identity_differs`, `test_scope_extension_is_refused_when_change_definition_differs_from_context` |
| AC-R9-2 | parité sélection/exécution | `TestPublicSensitiveActionSelection::test_select_action_and_execute_share_sensitive_action_verdict` |
| AC-R9-2 | isolation du cache par entrées et preuves | `TestPublicSensitiveActionSelection::test_selection_cache_includes_sensitive_inputs_and_decision_evidence` |
| AC-R9-2 | non-régression action non sensible | `TestPublicSensitiveActionSelection::test_non_sensitive_action_selection_remains_available_without_candidate_inputs` |
| AC-R15-7 | plafonds ordinaire/supervisé | `TestMandatoryEscalationToHuman`, `TestBlockingPolicyMatrix` |

### Résultats des tests

- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_policy.py -q` : 139 passed.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests -q` : 684 passed, 6 skipped.
- `git diff --check` : succès, sans erreur de whitespace.

### Prochaine étape

Remettre le correctif de revue sans créer de commit.
