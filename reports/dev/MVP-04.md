# MVP-04 — Définir le schéma SQLite MVP et les entités cœur

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** ✅ Stabilisé  
**Dépend de :** MVP-01 ✅ Terminé

## Objectif

Concevoir le modèle de données minimal pour le MVP en définissant les tables, relations et contraintes nécessaires pour gérer les cimetières, emplacements, concessions, personnes et défunts.

## Entités cœur implémentées

1. **cemeteries** — Cimetières d'une ou plusieurs communes
2. **plots** — Emplacements (cases) du cimetière
3. **concessions** — Droits de concession avec dates (acquisition, renouvellement, échéance)
4. **individuals** — Personnes physiques (concessionnaires, ayants droit, défunts)
5. **burials** — Associations défunt ↔ concession ↔ emplacement

## Tâches clés

- [x] Définir les tables et leurs colonnes
- [x] Établir les relations, contraintes et indices
- [x] Rédiger les migrations initiales (schema + seed data)
- [x] Valider la cardinalité et la normalisation
- [x] Documenter les choix de types et de contraintes

## Schéma implémenté

**Fichier :** `src-tauri/migrations/001_initial_schema.sql`

### Tables créées

#### cemeteries
- `id` : INTEGER PK AUTOINCREMENT
- `name` : TEXT NOT NULL
- `commune` : TEXT (optionnel)
- `capacity` : INTEGER (optionnel)
- `created_at` : TEXT ISO 8601 UTC
- `updated_at` : TEXT ISO 8601 UTC

#### plots
- `id` : INTEGER PK AUTOINCREMENT
- `cemetery_id` : INTEGER FK REFERENCES cemeteries(id)
- `section` : TEXT (optionnel, ex. "A", "B")
- `row` : INTEGER (optionnel, ex. 1, 2, ...)
- `number` : INTEGER (optionnel, ex. 1, 2, ...)
- `capacity` : INTEGER DEFAULT 1
- `status` : TEXT DEFAULT 'available' (available, occupied, reserved)
- `created_at`, `updated_at` : TEXT ISO 8601 UTC
- Index : idx_plots_cemetery_id

#### concessions
- `id` : INTEGER PK AUTOINCREMENT
- `cemetery_id` : INTEGER FK REFERENCES cemeteries(id)
- `plot_id` : INTEGER FK REFERENCES plots(id) (optionnel)
- `acquired_at` : TEXT ISO 8601 (optionnel)
- `expires_at` : TEXT ISO 8601 (optionnel)
- `renewed_at` : TEXT ISO 8601 (optionnel)
- `status` : TEXT DEFAULT 'active' (active, expired, abandoned)
- `created_at`, `updated_at` : TEXT ISO 8601 UTC
- Indexes : idx_concessions_cemetery_id, idx_concessions_plot_id

#### individuals
- `id` : INTEGER PK AUTOINCREMENT
- `name` : TEXT NOT NULL
- `email` : TEXT (optionnel)
- `phone` : TEXT (optionnel)
- `role` : TEXT NOT NULL (concessionnaire, heir, deceased, etc.)
- `created_at`, `updated_at` : TEXT ISO 8601 UTC

#### burials
- `id` : INTEGER PK AUTOINCREMENT
- `concession_id` : INTEGER FK REFERENCES concessions(id)
- `individual_id` : INTEGER FK REFERENCES individuals(id)
- `buried_at` : TEXT ISO 8601 (optionnel)
- `created_at`, `updated_at` : TEXT ISO 8601 UTC
- Indexes : idx_burials_concession_id, idx_burials_individual_id

## Modèles Rust créés

Tous les modèles sont sérialisables avec `serde`:
- ✅ `Cemetery`
- ✅ `Plot`
- ✅ `Concession`
- ✅ `Individual`
- ✅ `Burial`

Chaque modèle inclut un constructeur `.new()` avec timestamps auto-générés.

## Décisions architecturales

- **Soft delete :** pas implémenté pour MVP (suppression directe)
- **Timestamps :** ISO 8601 UTC en TEXT SQLite (compatible tous systèmes)
- **États :** TEXT (string) plutôt que enum (flexibilité, pas de migration si ajouts)
- **Nullable :** REFERENCES optionnelles pour certaines associations (plot_id en concessions)
- **Indexation :** FK + recherches fréquentes par cemetery_id
- **Foreign keys :** PRAGMA foreign_keys = ON au démarrage

## Problèmes connus

Aucun. Le schéma est :
- ✅ Compilable
- ✅ Testé (migrations_run test passe)
- ✅ Compatible avec Tauri/rusqlite

## Résultats des tests

- `test_migrations_run` ✅ Succès
  - 5 tables créées
  - Constraints et indexes appliqués
  - Foreign keys activées
- `cargo test --lib` ✅ 3/3 passent

## Prochaines étapes

1. MVP-05 : Implémenter les DTOs avec serialization complète
2. MVP-09 : Implémenter les repositories pour CRUD
3. MVP-10/11 : Implémenter les commandes Tauri pour cimeteries et emplacements
