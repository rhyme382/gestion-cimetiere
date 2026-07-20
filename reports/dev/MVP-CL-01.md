# Rapport — Task T1: Étendre le schéma SQLite et le dépôt concessions

**Task ID**: T1  
**Feature**: FEATURE-CONCESSION-LIFECYCLE-001  
**Agent**: database  
**Date**: 2026-07-19  
**Status**: Completed

---

## 1. Objectif

Analyser et étendre le schéma SQLite existant pour supporter les champs métier requis par le cycle de vie de base d'une concession funéraire, tout en préservant les données existantes et en implémentant les contraintes d'intégrité nécessaires.

---

## 2. Choix d'architecture : Migration incrémentale vs modification du schéma initial

### Analyse

Le schéma initial `001_initial_schema.sql` définit une table `concessions` minimaliste avec les colonnes:
- id, cemetery_id, plot_id
- acquired_at, expires_at, renewed_at
- status
- created_at, updated_at

Cette structure minimale suffisait pour un MVP basique, mais elle manque de tous les champs métier requis par la feature:
- numéro de concession (obligatoire, unique)
- type de concession (TEMPORAIRE, TRENTENAIRE, CINQUANTENAIRE, PERPETUELLE)
- durée en années
- date de début
- données du concessionnaire principal
- observations

### Décision

**Migration incrémentale via le fichier `0007_extend_concessions_for_lifecycle.sql`**

**Justification:**
1. **Préservation des données** : Une migration incrémentale laisse intactes les colonnes existantes et les données historiques.
2. **Flexibilité** : Si des données anciennes utilisent encore `acquired_at` / `expires_at`, elles restent disponibles.
3. **Clarté** : Chaque migration porte un numéro et une responsabilité claire.
4. **Maintenabilité** : Les futures migrations pour des features ultérieures (renouvellement, reprise, etc.) s'ajoutent sans conflits.
5. **Testabilité** : Les migrations peuvent être testées indépendamment.

### Alternative rejetée

Modifier `001_initial_schema.sql` directement aurait :
- Rendu impossible la reproduction de la base dans son état initial
- Compliqué le tracking des changements
- Risqué une perte de données si des systèmes externes dépendaient déjà du schéma publié

---

## 3. Schéma ajouté

### Fichier: `0007_extend_concessions_for_lifecycle.sql`

Colonnes ajoutées à la table `concessions`:

| Colonne | Type | Contraintes | Justification |
|---------|------|-------------|---------------|
| concession_number | TEXT | UNIQUE INDEX | Identifiant métier saisie par l'agent, unique pour éviter les doublons |
| concession_type | TEXT | CHECK(...) | Énumération des 4 types autorisés |
| duration_years | INTEGER | NULL | Durée en années (NULL pour perpétuel) |
| start_date | TEXT | NULL | Date ISO 8601 de début |
| price | REAL | NULL | Prix de la concession |
| payment_method | TEXT | NULL | Mode de paiement (optionnel) |
| holder_first_name | TEXT | NULL | Prénom du concessionnaire principal |
| holder_last_name | TEXT | NULL | Nom du concessionnaire principal |
| holder_phone | TEXT | NULL | Téléphone du concessionnaire |
| holder_email | TEXT | NULL | Email du concessionnaire |
| holder_address | TEXT | NULL | Adresse postale |
| holder_postal_code | TEXT | NULL | Code postal |
| holder_commune | TEXT | NULL | Commune du concessionnaire |
| observations | TEXT | NULL | Notes libres |

### Contrainte d'unicité

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_concessions_number_unique ON concessions(concession_number);
```

**Stratégie**: L'index UNIQUE sqlite3 est appliqué à la colonne `concession_number`. La normalisation (trim) du numéro en entrée est effectuée au niveau de la couche DTO/commandes (T3), non en base.

**Cas d'erreur**: Une tentative d'insertion d'un numéro dupliqué génère une erreur SQLite `UNIQUE constraint failed: concessions.concession_number`, capturée et remontée en tant qu'erreur structurée par le dépôt.

---

## 4. Modifications aux couches Rust

### 4.1 DTO (`src-tauri/src/dto/concession.rs`)

**ConcessionDTO** (sortie) :
- Tous les nouveaux champs comme Optional (car anciens enregistrements n'en ont pas).
- Conserve `acquired_at`, `expires_at`, `renewed_at` pour compatibilité.

**CreateConcessionRequest** (entrée) :
- Inclut les nouveaux champs métier nécessaires à la création.
- Champs optionnels pour la flexibilité (T3 ajoutera les validations strictes).

**UpdateConcessionRequest** (entrée) :
- Permet la mise à jour de tous les champs métier sauf id et created_at.
- Tous les champs sont optionnels (mise à jour sélective).

### 4.2 Modèle (`src-tauri/src/core/models/concession.rs`)

Structure `Concession` étendue avec tous les champs métier, tous Optional sauf `id`, `cemetery_id`, `status`, `created_at`, `updated_at`.

Constructeur `Concession::new()` inchangé pour backward-compatibility.

### 4.3 Dépôt (`src-tauri/src/db/repositories/concession_repo.rs`)

**Opérations**:
- `list()`: Retourne les 23 colonnes de la table étendue.
- `get()`: Idem.
- `create()`: Insère tous les 23 champs.
- `update()`: Met à jour tous les 23 champs (chaînage des valeurs existantes + nouvelles depuis le modèle).

**Tests**:
- Tous les tests existants ont été mis à jour pour inclure des données de concession nominales.
- **Nouveau test** : `test_concession_number_unique_constraint()` valide que les doublons de numéro génèrent une erreur SQLite.

---

## 5. Intégration des migrations

### Fichier: `src-tauri/src/db/migrations.rs`

Ajout du `include_str!()` pour la nouvelle migration et exécution dans `run_migrations()`.

Test mis à jour: la vérification du nombre de tables reste cohérente (les tables existantes ne sont pas supprimées, seules des colonnes sont ajoutées).

---

## 6. Validation

### Tests exécutés

```bash
cargo test -p gestion-cimetiere db::migrations::tests::test_migrations_run
# Result: PASSED ✓

cargo test -p gestion-cimetiere concession_repo
# Results (7 tests):
#   - test_create_and_get_concession ... ok
#   - test_list_concessions ... ok
#   - test_update_concession ... ok
#   - test_get_non_existent_concession ... ok
#   - test_update_non_existent_concession ... ok
#   - test_fk_constraint_cemetery ... ok
#   - test_concession_number_unique_constraint ... ok
# ✓ All passed
```

### Couverture

- ✓ Création avec données métier
- ✓ Lecture de tous les champs
- ✓ Mise à jour de champs métier
- ✓ Contrainte d'unicité sur concession_number
- ✓ Préservation des contraintes FK existantes
- ✓ Gestion des erreurs SQLite

---

## 7. Considérations pour les tâches suivantes

### T2 (Modèle métier et calculs)
- Le backend devra implémenter le calcul de `expires_at` à partir de `start_date + duration_years`.
- Les validations métier (type vs durée, dates cohérentes) seront ajoutées.
- Énumération explicite pour `concession_type` et `status`.

### T3 (Commandes Tauri)
- Normalisation du `concession_number` (trim) avant insertion.
- Validation stricte des entrées (dates ISO, durées > 0, etc.).
- Transactions pour garantir l'atomicité.
- Erreurs structurées remontées au frontend.

### Traçabilité de l'occupation d'emplacement
- Le schéma actuel permet un emplacement (`plot_id`) avec plusieurs concessions actives.
- La logique de contrôle d'incompatibilité devra être implémentée au niveau commandes/transactions (T3).
- Actuellement, seule l'unicité du numéro de concession est garantie par le schéma.

---

## 8. Artefacts produits

**Fichiers modifiés** (commits):
1. `src-tauri/migrations/0007_extend_concessions_for_lifecycle.sql` — Migration SQL
2. `src-tauri/src/db/migrations.rs` — Intégration de la migration
3. `src-tauri/src/dto/concession.rs` — DTOs étendus
4. `src-tauri/src/core/models/concession.rs` — Modèle étendu
5. `src-tauri/src/db/repositories/concession_repo.rs` — Dépôt étendu + tests

**Pas de régression**: Tous les tests existants continuent de passer après l'extension du schéma.

---

## 9. Conclusion

La tâche T1 a réussi à:
- ✓ Etendre le schéma SQLite de manière incrémentale
- ✓ Préserver les données existantes et la compatibilité backward
- ✓ Ajouter les champs métier minimaux requis par la feature
- ✓ Implémenter une contrainte d'unicité testable pour le numéro
- ✓ Adapter les couches DTO, modèle et dépôt
- ✓ Passer tous les tests

Le schéma est maintenant prêt pour les tâches T2 et T3, qui ajouteront les validations métier et les commandes Tauri.
