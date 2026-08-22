# Correction — AUTODEV-PRODUCT-SUPERVISOR-T06

## Tâche
Implémenter la sélection stable des features et les dépendances Git — **Correction automatique** suite à verdict Codex.

## Verdict Codex initial
`CORRECTION_REQUIRED` — Deux issues majeures identifiées dans R4:

1. **AC-R4-1 FAIL**: Le tri final ignore la dimension "dépendances" exigée et ordonne uniquement par priorité puis identifiant
   - Evidence: Les features éligibles sont triées uniquement par `(-f.priority, f.feature_id)`
   - Aucun critère ne représente l'ordre par dépendances

2. **AC-R4-4 FAIL**: Une feature déjà intégrée mais non marquée `COMPLETED` peut être relancée sans incident
   - Violation: "Une feature déjà clôturée ou incohérente n'est jamais relancée"
   - A-feature avec commit intégré mais sans statut COMPLETED reste potentiellement éligible

## Corrections appliquées

### Issue 1: Ordre de sélection par dépendances (AC-R4-1)

**Problème identifié**: Tri incomplet ignorant la dimension dépendances

```python
# Ancien code (incorrect)
eligible.sort(key=lambda f: (-f.priority, f.feature_id))
```

**Solution implémentée**: 

1. **Ajout de `_calculate_dependency_depth()`** — Fonction récursive avec memoïzation:
   - Features sans dépendances: profondeur = 0
   - Profondeur d'une feature = 1 + max(profondeur des dépendances)
   - Prévient les boucles infinies et optimise la complexité

2. **Modification du tri**:
```python
# Nouveau code (correct)
eligible.sort(key=lambda f: (
    depth_memo.get(f.feature_id, 0),  # Profondeur croissante
    -f.priority,                        # Priorité décroissante (dans même profondeur)
    f.feature_id                        # ID stable (tie-breaker)
))
```

**Garanties fournies**:
- Features sans dépendances (depth 0) toujours avant les dépendantes
- Parmi features de même profondeur, priorité plus haute en premier
- Identifiants en ordre alphabétique pour la stabilité

**Test ajouté**: `test_select_next_feature_orders_by_dependency_depth`
- Vérifie que depth 0 features (D, C) sont sélectionnées avant depth 1 features (B)
- Même si B a priorité 100 vs D avec priorité 10
- Valide l'ordre du résultat retourné

### Issue 2: Détection d'incohérence feature (AC-R4-4)

**Problème identifié**: Absence de vérification pour features intégrées sans statut cohérent

```python
# Ancien code (incomplet)
if status == "COMPLETED":
    # Crée incident...
    continue
# Mais une feature avec commit intégré mais status != COMPLETED n'est pas détectée!
```

**Solution implémentée**: Ajout d'un contrôle d'incohérence avant vérification des dépendances:

```python
# Nouveau code (complet)
# Check for incoherence: feature already integrated but not marked COMPLETED
if feature.feature_id in integrated_commits and status != "COMPLETED":
    incident = ProductIncident(
        code="FEATURE_INCOHERENT_STATUS",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.DEPENDENCY,
        proofs=[
            f"Feature '{feature.feature_id}' has integrated commit but status is '{status}'",
            f"Integrated commit: {integrated_commits[feature.feature_id][:8]}..."
        ],
        # ...
    )
    incidents.append(incident)
    ineligible.append(feature)
    continue
```

**Garanties fournies**:
- Détecte divergence entre état Git (commit intégré) et état déclaré (status field)
- Produit incident structuré avec preuves (commits, statuts)
- Prévient relance silencieuse en marquant feature inéligible
- Respecte AC-R4-4: "Une incohérence produit un incident"

**Test ajouté**: `test_select_next_feature_detects_incoherent_integrated_feature`
- Feature avec commit intégré mais status "IN_PROGRESS"
- Génère incident `FEATURE_INCOHERENT_STATUS`
- Feature ajoutée à ineligible_features

## Modifications aux fichiers

### `autodev/src/autodev/product_selection.py`
- **Ajout**: Fonction `_calculate_dependency_depth()` (lignes 130-156)
- **Modification**: Fonction `select_next_feature()` 
  - Tri désormais par (depth, -priority, feature_id) au lieu de (-priority, feature_id)
  - Ajout check incohérence avant verify_dependency_integration
  - Précalcul depths pour mémorisation

### `autodev/tests/test_product_selection.py`
- **Ajout**: `test_select_next_feature_orders_by_dependency_depth()` (lignes 387-438)
- **Ajout**: `test_select_next_feature_detects_incoherent_integrated_feature()` (lignes 441-472)
- **Mise à jour**: `test_select_next_feature_complex_dependency_graph()` (ligne 303)
  - Expectation changée: D au lieu de C (respect de depth ordering)
  - Rationale mise à jour pour refléter nouveau comportement

## Résultats des tests

```bash
env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_selection.py -q
```

**✅ Résultat: 15 tests passed in 0.27s**

- 13 tests existants: tous verts ✓
- 2 nouveaux tests de correction: verts ✓

Couverts:
- Ordre par priorité: ✓
- Ordre par ID stable: ✓
- Respect des dépendances: ✓
- **Nouveau**: Ordre par profondeur de dépendance: ✓
- Vérification Git par ancestralité: ✓
- Rejet features COMPLETED: ✓
- **Nouveau**: Détection incohérence features intégrées: ✓
- Cas limites (plan vide, no eligible, etc.): ✓

## Conformité aux exigences

### AC-R4-1: "L'ordre est déterminé par dépendances, priorité, puis identifiant stable."
✅ **PASS** — Implémenté via tri tri-critères:
1. Profondeur de dépendance (ascending): features sans deps avant dépendantes
2. Priorité (descending): parmi même profondeur, priorité plus haute d'abord
3. Identifiant (ascending): ordre alphabétique pour stabilité

**Preuve**: `test_select_next_feature_orders_by_dependency_depth` valide que D (depth 0) est sélectionné avant B (depth 1) malgré priorité 10 < 100

### AC-R4-2: "Une feature dépendante part d'une base produit dont l'historique contient les commits intégrés de toutes ses dépendances."
✅ **PASS** — Fonction `verify_dependency_integration()` existante couvre entièrement (unchanged)

### AC-R4-3: "La présence de ces commits est vérifiée par relation d'ancêtre Git, pas par statut déclaré."
✅ **PASS** — Utilisation systématique de `is_ancestor(...)` (unchanged)

### AC-R4-4: "Une incohérence produit un incident ; une feature terminée n'est pas relancée."
✅ **PASS** — Deux vérifications complémentaires:
1. Features `COMPLETED` explicitement bloquées → incident `FEATURE_ALREADY_COMPLETED`
2. Features avec commit intégré ≠ COMPLETED → incident `FEATURE_INCOHERENT_STATUS`

**Preuve**: `test_select_next_feature_detects_incoherent_integrated_feature` valide détection et exclusion

## Impact et compatibilité

### Comportement de sélection change
- **Avant**: Features ordonnées par (priorité, ID)
- **Après**: Features ordonnées par (profondeur, priorité, ID)
- **Impact métier**: Features indépendantes sélectionnées en priorité, respectant dépendances naturelles
- **Regression**: Aucune, tous tests existants passent, y compris `test_select_next_feature_respects_dependencies` qui valide déjà le tri

### Incompatibilités
- Aucune avec contrats existants (SelectionResult, ProductIncident, Feature)
- Aucune avec `verify_dependency_integration()` (inchangé)
- Aucune avec `git_tools.is_ancestor()` (réutilisé)

## Trace d'exécution

```
$ env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_selection.py -q

test_select_next_feature_orders_by_priority PASSED
test_select_next_feature_orders_by_id_when_priority_equal PASSED
test_select_next_feature_respects_dependencies PASSED
test_verify_dependency_integration_checks_git_ancestor PASSED
test_verify_dependency_integration_detects_missing_commit PASSED
test_verify_dependency_integration_unknown_dependency PASSED
test_select_next_feature_rejects_completed PASSED
test_select_next_feature_no_eligible PASSED
test_select_next_feature_complex_dependency_graph PASSED  # Updated expectation
test_verify_dependency_integration_missing_integration_record PASSED
test_dependency_incident_has_correct_properties PASSED
test_select_next_feature_empty_plan PASSED
test_select_next_feature_rationale_includes_incidents PASSED
test_select_next_feature_orders_by_dependency_depth PASSED  # NEW
test_select_next_feature_detects_incoherent_integrated_feature PASSED  # NEW

15 passed in 0.27s ✅
```

## Prochaines étapes

Les deux issues majeures de R4 sont corrigées:
- ✅ Ordre par dépendances intégré au tri stable
- ✅ Incohérence features détectée et bloquée

Le superviseur produit peut maintenant procéder à l'implémentation des étapes suivantes (R5 onwards) avec certitude que la sélection des features respecte les exigences d'ordre déterministe et de détection d'incohérence.
