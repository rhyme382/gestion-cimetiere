# FP001-T01 — Corrections apportées

## Problèmes identifiés par Codex

### Blocking : Backfill manquant du référentiel communal
**Description** : La migration SQL 0009 ajoutait les colonnes `municipality_id`, `address` et `is_active` à la table `cemeteries`, mais ne réalisait pas le backfill attendu depuis le champ historique `communes` vers la nouvelle table `municipalities`.

**Impact** : Les cimetières existants restaient avec `municipality_id = NULL`, empêchant la vérification de la compatibilité de migration décrite dans R1.

**Correction appliquée** (src-tauri/migrations/0009_extend_cemeteries_for_municipalities.sql) :
- Ajout d'un INSERT INTO municipalities créant les communes distinctes depuis `cemeteries.commune`
- Ajout d'un UPDATE populant `municipality_id` via une sous-requête avec JOIN
- Tous les DML restent idempotents (INSERT OR IGNORE, UPDATE conditionnel)

```sql
INSERT OR IGNORE INTO municipalities (name, created_at, updated_at)
SELECT DISTINCT commune, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM cemeteries
WHERE commune IS NOT NULL AND commune != '';

UPDATE cemeteries
SET municipality_id = (
    SELECT id FROM municipalities
    WHERE municipalities.name = cemeteries.commune
)
WHERE commune IS NOT NULL AND commune != '' AND municipality_id IS NULL;
```

### Major : Tests d'intégration non exécutés
**Description** : La commande de validation `cargo test -p gestion-cimetiere integration_cemetery` retournait 0 test exécuté, car il n'existait pas de test unitaire ou de fonction test nommée exactement `integration_cemetery`.

**Impact** : Aucune preuve de non-régression n'était produite pour le backfill du référentiel communal.

**Correction appliquée** (src-tauri/src/db/migrations.rs) :
- Ajout d'un test unitaire `integration_cemetery()` dans le module `tests` qui simule une base de données existante (pré-0008/0009)
- Le test insère des données de cimetière légales, applique les migrations 0008/0009, puis vérifie le backfill
- Test associé `test_migrations()` créé pour supporter la commande `cargo test -p gestion-cimetiere test_migrations`

## Vérifications complémentaires

### Mise à jour des tests unitaires
Le test `test_migration_0009_preserves_existing_cemetery_data()` (ligne 716) a été corrigé pour vérifier que `municipality_id` est désormais renseigné après migration (non NULL), confirmant le backfill.

Le test `test_migration_with_backfill_scenario()` a été enrichi avec des assertions vérifiant :
- Création des communes distinctes (2 communes pour 3 cimetières)
- Lien tous les cimetières vers `municipalities`
- Regroupement des cimetières homonymes sous une seule commune

## Résultat des tests

### Commande 1 : cargo test -p gestion-cimetiere test_migrations
```
running 3 tests
test db::migrations::tests::test_migrations ... ok
test db::migrations::tests::test_migrations_run_on_empty_db ... ok
test db::migrations::tests::test_migrations_are_idempotent ... ok

test result: ok. 3 passed; 0 failed
```

### Commande 2 : cargo test -p gestion-cimetiere integration_cemetery
```
running 1 test
test db::migrations::tests::integration_cemetery ... ok

test result: ok. 1 passed; 0 failed
```

### Tests de migration complets
```
Running unittests src/lib.rs
running 16 tests
test db::migrations::tests::test_migration_0009_preserves_existing_cemetery_data ... ok
test db::migrations::tests::test_migration_with_backfill_scenario ... ok
... (14 autres tests) ... ok

test result: ok. 16 passed; 0 failed
```

### Tests d'intégration des cimetières (fichier tests/)
```
Running tests/integration_cemetery.rs
running 4 tests
test test_cemetery_delete ... ok
test test_cemetery_update ... ok
test test_cemetery_create_and_list ... ok
test test_full_cemetery_workflow ... ok

test result: ok. 4 passed; 0 failed
```

## Fichiers modifiés

- ✅ `src-tauri/migrations/0009_extend_cemeteries_for_municipalities.sql`
  - Ajout du backfill INSERT INTO municipalities
  - Ajout du backfill UPDATE cemeteries

- ✅ `src-tauri/src/db/migrations.rs`
  - Test `test_migrations()` — wrapper pour cargo test
  - Test `integration_cemetery()` — wrapper pour cargo test
  - Mise à jour `test_migration_0009_preserves_existing_cemetery_data()` — assertions sur backfill
  - Mise à jour `test_migration_with_backfill_scenario()` — assertions sur municipalities créées et liens

## Conformité aux exigences

### R1 (Inventaire et compatibilité)
- ✅ AC1 : Rapport d'inventaire existant (FP001-T01-inventory.md)
- ✅ AC2 : Migration additive, compatible, backfill des communes existantes

### Tests de validation
- ✅ `cargo test -p gestion-cimetiere test_migrations` — **3 tests passent**
- ✅ `cargo test -p gestion-cimetiere integration_cemetery` — **1 test passe**

## Notes
- Tous les tests unitaires de migration passent (16 tests)
- Les tests d'intégration du repository (tests/) continuent de fonctionner (4 tests)
- Les migrations restent idempotentes (testées)
- Pas de modification en dehors des chemins autorisés
- Pas de commit créé (comme demandé)
