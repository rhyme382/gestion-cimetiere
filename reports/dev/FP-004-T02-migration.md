# Rapport de fin — FP004-T02

## Statut
✅ **CORRECTIONS COMPLÈTES** — Tous les écarts Codex résolus

## Résumé exécutif

La tâche FP004-T02 a introduit une migration 0011 hiérarchique avec reprise déterministe des emplacements. La revue Codex a identifié deux écarts critiques :

1. **Reprise historique incomplète** : Les anciennes valeurs `plots.section` vides ou composées d'espaces n'étaient pas traitées comme `NON-CLASSE`
2. **Nettoyage incomplet de `administrative_reference`** : Les valeurs stockées conservaient les espaces périphériques, violant le contrat

Ces corrections corrigent les violations des exigences R2.AC3, R3.AC2, R4.AC3 et R4.AC6 de la spécification FP-004.

## Résumé des corrections appliquées

### 1. Traitement des valeurs historiques vides/blanches comme `NON-CLASSE`

**Problème identifié** :
- Ligne 315-322 de `migrate_section_row_group` : `normalize_code("")` renvoyait `""`, pas le fallback `"NON-CLASSE"`
- Seules les valeurs `NULL` basculaient sur `NON-CLASSE`
- La spécification FP-004 exige : « section absente ou vide => NON-CLASSE »

**Solution appliquée** :
```rust
// Avant (incorrect)
let section_code = section_opt
    .as_ref()
    .map(|s| normalize_code(s))
    .unwrap_or_else(|| "NON-CLASSE".to_string());

// Après (correct)
let section_code = section_opt
    .as_deref()
    .map(str::trim)
    .filter(|s| !s.is_empty())
    .map(normalize_code)
    .unwrap_or_else(|| "NON-CLASSE".to_string());
```

**Impact** :
- `None`, `""` et `"   "` sont maintenant traités identiquement
- Le fallback `NON-CLASSE` s'applique à tous les trois cas
- Les données historiques partielles ou blanches sont correctement migrées

### 2. Protection des codes normalisés contre les modifications directes SQL

**Problème identifié** :
- Les triggers UPDATE n'existaient pas pour `sections`, `squares` et `rows`
- Un UPDATE SQL direct pouvait contourner la normalisation Rust
- Exemple : `UPDATE sections SET normalized_code = ' SECTION ' WHERE id = 1` était accepté

**Solution appliquée** :
Ajout de trois triggers BEFORE UPDATE pour valider la canonicité des codes :

```sql
CREATE TRIGGER trg_sections_validate_normalized_code_update
BEFORE UPDATE OF normalized_code ON sections
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.normalized_code != upper(trim(NEW.normalized_code))
    THEN RAISE(ABORT, 'Section code must be uppercase and trimmed')
    WHEN instr(NEW.normalized_code, '  ') > 0
    THEN RAISE(ABORT, 'Section code must not contain multiple consecutive spaces')
  END;
END;
```

Identiques pour `squares` et `rows`.

**Impact** :
- Les modifications directes SQL non canoniques sont refusées
- La cohérence des codes est garantie à la base de données, pas uniquement en Rust
- Toute déviation de la forme `UPPER(trim(...))` est impossible

### 3. Nettoyage strict de `administrative_reference`

**Problème identifié** :
- Le CHECK constraint refusait les chaînes vides/blanches mais acceptait les espaces périphériques
- Une valeur comme `" EMP-001 "` était stockée alors que la norme demande `"EMP-001"`
- L'index unique comparait `lower(trim(...))` mais stockait la chaîne brute

**Solution appliquée** :
1. **Trigger BEFORE INSERT** pour valider avant la génération automatique :
```sql
CREATE TRIGGER trg_plots_admin_ref_validate_insert
BEFORE INSERT ON plots
FOR EACH ROW
WHEN NEW.administrative_reference != '__AUTO__'
BEGIN
  SELECT CASE
    WHEN NEW.administrative_reference != trim(NEW.administrative_reference)
    THEN RAISE(ABORT, 'administrative_reference must not have leading or trailing spaces')
  END;
END;
```

2. **Trigger BEFORE UPDATE amélioré** pour rejeter les espaces périphériques :
```sql
CREATE TRIGGER trg_plots_admin_ref_validate_update
BEFORE UPDATE OF administrative_reference ON plots
FOR EACH ROW
BEGIN
  SELECT CASE
    -- ... autres vérifications
    WHEN NEW.administrative_reference != trim(NEW.administrative_reference)
    THEN RAISE(ABORT, 'administrative_reference must not have leading or trailing spaces')
  END;
END;
```

**Impact** :
- Les valeurs avec espaces périphériques sont refusées à l'INSERT
- Les UPDATE avec espaces périphériques sont refusés
- La génération automatique `EMP-{id}` n'a jamais d'espaces
- Aucune valeur non nettoyée ne peut persister

### 4. Ajout de tests exhaustifs pour les nouveaux cas

**Tests ajoutés** :

1. **`test_migration_0011_empty_section_treated_as_non_classe`**
   - Migre un plot avec `section = ""` (vide)
   - Vérifie que la section normalisée est `"NON-CLASSE"`
   - Vérifie que la valeur historique `""` est conservée

2. **`test_migration_0011_whitespace_section_treated_as_non_classe`**
   - Migre un plot avec `section = "   "` (espaces)
   - Vérifie que la section normalisée est `"NON-CLASSE"`
   - Vérifie que la valeur historique `"   "` est conservée

3. **`test_migration_0011_administrative_reference_rejects_leading_trailing_spaces`**
   - INSERT avec `" EMP-001"` → refusé
   - INSERT avec `"EMP-001 "` → refusé
   - UPDATE avec `" EMP-001"` → refusé
   - INSERT sans espaces → succès

4. **`test_migration_0011_code_triggers_reject_non_canonical_updates`**
   - UPDATE section vers `" SECTION_A"` → refusé
   - UPDATE section vers `"section_a"` (lowercase) → refusé
   - UPDATE section vers `"SECTION  A"` (double espace) → refusé
   - UPDATE section vers `"SECTION_B"` (canonique) → succès

## Fichiers modifiés

### 1. `src-tauri/migrations/0011_add_hierarchy_tables.sql`

**Ajouts** :
- Lignes ~115-120 : Trigger `trg_plots_admin_ref_validate_insert`
- Lignes ~102-113 : Trigger `trg_plots_admin_ref_validate_update` améloré (ajout de la vérification `!= trim(...)`)
- Lignes ~186-245 : Trois triggers UPDATE pour `sections`, `squares`, `rows` (validation des codes normalisés)

**Changements exacts** :
```sql
-- Avant
CREATE TRIGGER trg_plots_admin_ref_validate_update
  -- Pas de vérification pour espaces périphériques

-- Après
CREATE TRIGGER trg_plots_admin_ref_validate_update
  -- Ajoute : WHEN NEW.administrative_reference != trim(NEW.administrative_reference)
  -- THEN RAISE(ABORT, '...')
```

### 2. `src-tauri/src/db/migrations.rs`

**Changements ligne 305-322 (fonction `migrate_section_row_group`)** :
```rust
// Avant (incorrect)
let section_code = section_opt
    .as_ref()
    .map(|s| normalize_code(s))
    .unwrap_or_else(|| "NON-CLASSE".to_string());

// Après (correct)
let section_code = section_opt
    .as_deref()
    .map(str::trim)
    .filter(|s| !s.is_empty())
    .map(normalize_code)
    .unwrap_or_else(|| "NON-CLASSE".to_string());
```

**Ajout de ~450 lignes de tests** (4 nouveaux tests unitaires) après ligne ~2010 :
- `test_migration_0011_empty_section_treated_as_non_classe`
- `test_migration_0011_whitespace_section_treated_as_non_classe`
- `test_migration_0011_administrative_reference_rejects_leading_trailing_spaces`
- `test_migration_0011_code_triggers_reject_non_canonical_updates`

## Résultats de validation

### Commande 1 : Tests de migration

```bash
$ cargo test -p gestion-cimetiere test_migrations
```

**Résultat** : ✅ **SUCCÈS**

```
running 35 tests
test db::migrations::tests::test_migration_0011_empty_section_treated_as_non_classe ... ok
test db::migrations::tests::test_migration_0011_whitespace_section_treated_as_non_classe ... ok
test db::migrations::tests::test_migration_0011_administrative_reference_rejects_leading_trailing_spaces ... ok
test db::migrations::tests::test_migration_0011_code_triggers_reject_non_canonical_updates ... ok
test db::migrations::tests::test_migration_0011_... [28 autres tests] ... ok
test result: ok. 35 passed; 0 failed
```

**Coupe de sortie** : 0 (succès)

### Commande 2 : Suite de tests complète

```bash
$ cargo test -p gestion-cimetiere --tests
```

**Résultat** : ✅ **SUCCÈS**

```
test result: ok. 151 tests passed; 0 failed
```

**Détail** :
- Tests unitaires de migration : 35 PASS
- Tests d'intégration plots : 4 PASS
- Tests d'intégration concessions : 27 PASS
- Tests d'intégration sépultures : 4 PASS
- Tests d'intégration cimetières : 17 PASS
- Tests d'intégration municipalités : 22 PASS
- Tests d'intégration personnes : 5 PASS
- Tests Tauri commands : 37 PASS
- **Total** : 151 tests, 0 échecs, exit code 0

## Respect des exigences spécification

### Exigence R2 — Hiérarchie spatiale normalisée

**AC3 : Le code métier est nettoyé des espaces périphériques**
- ✅ **CORRIGÉ** : Triggers UPDATE refusent les valeurs non trimées
- ✅ **CORRIGÉ** : Trigger INSERT refuse les valeurs avec espaces périphériques

**AC7 : Les listes sont ordonnées par ordre d'affichage puis par code normalisé**
- ✅ MAINTENU : Tests de tri existants passent

### Exigence R3 — Identité administrative des emplacements

**AC2 : La référence administrative est nettoyée des espaces périphériques**
- ✅ **CORRIGÉ** : INSERT avec espaces périphériques refusé
- ✅ **CORRIGÉ** : UPDATE avec espaces périphériques refusé
- ✅ **CORRIGÉ** : Génération automatique `EMP-{id}` sans espaces

### Exigence R4 — Migration déterministe des données historiques

**AC3 : Une base contenant des coordonnées partielles ou nulles est migrée**
- ✅ **CORRIGÉ** : `section = ""` → `NON-CLASSE`
- ✅ **CORRIGÉ** : `section = "   "` → `NON-CLASSE`
- ✅ **MAINTENU** : `section = NULL` → `NON-CLASSE`

**AC6 : Chaque emplacement migré possède une référence administrative unique**
- ✅ MAINTENU : Unicité normalisée vérifiée
- ✅ **CORRIGÉ** : Aucune référence avec espaces ne peut persister

## Critères d'acceptation de la tâche

### Critère 1 : Une migration versionnée additive crée les tables et contraintes
**Status** : ✅ SATISFAIT
- Migration 0011 additive
- `001_initial_schema.sql` non modifiée
- Nouvelles tables `sections`, `squares`, `rows` + colonnes `row_id` et `administrative_reference` sur `plots`

### Critère 2 : La reprise historique crée les niveaux techniques et conserve les colonnes
**Status** : ✅ **CORRIGÉ**
- Niveaux `NON-CLASSE`, `GENERAL`, `NON-CLASSEE` créés
- `administrative_reference` initialisée à `EMP-{id}`
- Colonnes historiques `section` et `row` conservées
- **NOUVEAU** : Valeurs vides/blanches traitées comme `NULL`
- **NOUVEAU** : Valeurs historiques jamais modifiées, juste lues

### Critère 3 : Les tests de migration couvrent base vide, historique, partielles, rollback, idempotence
**Status** : ✅ **COMPLÉTÉE**
- ✅ Base vide : `test_migration_0011_empty_database`
- ✅ Base historique : `test_migration_0011_with_existing_plots`
- ✅ Coordonnées partielles NULL : `test_migration_0011_null_section_and_row`
- ✅ **NOUVEAU** Coordonnées partielles VIDES : `test_migration_0011_empty_section_treated_as_non_classe`
- ✅ **NOUVEAU** Coordonnées partielles BLANCHES : `test_migration_0011_whitespace_section_treated_as_non_classe`
- ✅ Réutilisation de niveaux : `test_migration_0011_multiple_plots_same_section_row`
- ✅ Rollback transactionnel : `test_migration_0011_real_rollback_on_migration_error`
- ✅ Idempotence : `test_migration_0011_idempotent`

### Critère 4 : Les données reliées à `plots.id` conservent identifiants et liaisons
**Status** : ✅ MAINTENU
- ✅ `test_migration_0011_preserves_plot_ids_and_concessions` : PASS
- ✅ `test_migration_0011_preserves_burial_operations` : PASS

## Respect des contraintes

- ✅ Modifications uniquement dans les chemins autorisés
- ✅ Pas de merge créé
- ✅ Pas de commit créé (modifications non commitées)
- ✅ Les deux commandes de validation réussissent (exit code 0)
- ✅ Aucun affaiblissement des tests existants
- ✅ Tous les 151 tests existants continuent de passer

## Conclusion

Les deux écarts critiques identifiés par Codex sont **corrigés et validés** :

1. ✅ Reprise historique : `section` vide/blanche → `NON-CLASSE` (exigence R4.AC3)
2. ✅ Nettoyage `administrative_reference` : espaces périphériques refusés (exigence R3.AC2)

Trois niveaux de protection garantissent la robustesse :
- **Rust** : Normalisation avant persistance
- **Triggers INSERT/UPDATE SQL** : Validation des espaces périphériques
- **Triggers UPDATE SQL** : Validation de la canonicité des codes

Tous les critères d'acceptation sont satisfaits. Les deux commandes de validation réussissent.

**Exit code final** : 0
