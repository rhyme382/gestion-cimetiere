# Rapport de fin — FP004-T03 (CORRECTION FINALE)

## Statut
✅ **COMPLET** — Tous les critères d'acceptation de la tâche satisfaits, contrat applicatif sécurisé

## Résumé exécutif

FP004-T03 introduit les modèles Rust et DTOs hiérarchiques pour la structure de cimetière (sections, carrés, rangées) et enrichit `PlotDTO` avec une référence administrative et un chemin hiérarchique. L'infrastructure d'erreurs applicatives est complétée pour différencier les erreurs de lecture par niveau, sans exposer aucun détail SQLite brut dans le contrat public.

### Corrections finales appliquées

1. **Sécurisation du contrat applicatif** (CRITICAL)
   - ✅ Modifié la sérialisation de `AppError::Database` pour neutraliser le message SQLite brut
   - ✅ Remplacé `message: self.to_string()` par une distribution des messages par variante d'erreur
   - ✅ `AppError::Database` sérialise maintenant `"An unexpected database error occurred"` au lieu du détail rusqlite
   - ✅ Ajout de 2 tests unitaires **autoritatifs** :
     - `app_error_database_does_not_expose_raw_sqlite_message` — teste une erreur SQLite réelle et prouve qu'elle est neutralisée
     - `app_error_database_serializes_with_safe_message` — teste une autre variante d'erreur SQLite

2. **Infrastructure d'erreurs pour la hiérarchie** (COMPLETE)
   - ✅ `NotFoundKind` enum supporte Cemetery, Section, Square, Row, Plot
   - ✅ Codes d'erreur différenciés : `CEMETERY_NOT_FOUND`, `SECTION_NOT_FOUND`, `SQUARE_NOT_FOUND`, `ROW_NOT_FOUND`, `PLOT_NOT_FOUND`
   - ✅ Helpers : `AppError::with_kind()`, `AppError::kind_from_message()`, `NotFoundKind::as_str()`
   - ✅ 12 tests unitaires couvrent la différenciation, la sérialisation et la neutralisation SQLite

---

## Fichiers créés et modifiés

### Modèles Rust — Nouveaux fichiers

1. **`src-tauri/src/core/models/section.rs`**
   - Modèle `Section` avec champs :
     - `id: i64` — identifiant technique
     - `cemetery_id: i64` — référence au cimetière
     - `normalized_code: String` — code normalisé (uppercase, trimé)
     - `display_label: String` — étiquette pour l'affichage
     - `display_order: i32` — ordre de tri
     - `is_active: bool` — statut soft-delete
     - `created_at`, `updated_at` — timestamps
   - Constructeur `new()` avec defaults
   - Tests unitaires

2. **`src-tauri/src/core/models/square.rs`**
   - Modèle `Square` avec structure identique, `section_id` pour la hiérarchie
   - Constructeur et tests unitaires

3. **`src-tauri/src/core/models/row.rs`**
   - Modèle `Row` avec `square_id` pour référencer le carré parent
   - Constructeur et tests unitaires

### DTOs — Nouveaux fichiers

1. **`src-tauri/src/dto/section.rs`**
   - `SectionDTO` pour la sérialisation Tauri (read-only en FP-004)

2. **`src-tauri/src/dto/square.rs`**
   - `SquareDTO` pour la sérialisation Tauri (read-only en FP-004)

3. **`src-tauri/src/dto/row.rs`**
   - `RowDTO` pour la sérialisation Tauri (read-only en FP-004)

### Fichiers modifiés

1. **`src-tauri/src/core/models/mod.rs`**
   ```rust
   pub mod row;
   pub mod section;
   pub mod square;

   pub use row::Row;
   pub use section::Section;
   pub use square::Square;
   ```

2. **`src-tauri/src/dto/mod.rs`**
   ```rust
   pub mod row;
   pub mod section;
   pub mod square;

   pub use row::RowDTO;
   pub use section::SectionDTO;
   pub use square::SquareDTO;
   ```

3. **`src-tauri/src/dto/plot.rs`**
   - `HierarchicalPathDTO` — représente le chemin spatial complet (section → carré → rangée)
   - **PlotDTO** enrichi directement (pas de wrapper) :
     ```rust
     pub struct PlotDTO {
         pub id: i64,
         pub cemetery_id: i64,
         pub section: Option<String>,                        // Historique
         pub row: Option<i32>,                               // Historique
         pub number: Option<i32>,                            // Historique
         pub capacity: i32,
         pub status: String,
         #[serde(default)]
         pub administrative_reference: Option<String>,      // Nouveau
         #[serde(default)]
         pub hierarchical_path: Option<HierarchicalPathDTO>, // Nouveau
         pub created_at: String,
         pub updated_at: String,
     }
     ```
   - Tous les tests de PlotDTO passent

4. **`src-tauri/src/errors/mod.rs`** (CORRIGÉ)
   - Infrastructure de typage d'erreurs `NotFoundKind` :
     ```rust
     pub enum NotFoundKind {
         Cemetery, Section, Square, Row, Plot,
         Concession, Individual, BurialOperation, Generic,
     }
     ```
   - Implémentation de `NotFoundKind::as_str()` pour obtenir les codes :
     - `"CEMETERY_NOT_FOUND"`, `"SECTION_NOT_FOUND"`, `"SQUARE_NOT_FOUND"`, `"ROW_NOT_FOUND"`, `"PLOT_NOT_FOUND"`
   - **Sérialisation sécurisée** :
     - `NotFound` → utilise le code spécifique du type
     - `InvalidInput` → retourne le message fourni
     - `Duplicate` → retourne le message fourni
     - **`Database` → NEUTRALISÉ : retourne `"An unexpected database error occurred"` au lieu du détail SQLite**
     - `Internal` → retourne le message fourni
   - Helpers : `AppError::with_kind()`, `AppError::kind_from_message()`
   - 12 tests unitaires couvrent tous les cas

5. **`src-tauri/src/db/repositories/plot_repo.rs`**
   - Adaptation des initialiseurs existants pour les nouveaux champs optionnels :
     - `administrative_reference: None`
     - `hierarchical_path: None`
   - Préserve la compilation et la compatibilité

---

## Critères d'acceptation de la tâche

### CA1 : Les nouveaux modèles et DTO Rust représentent explicitement section, carré, rangée et chemin spatial complet

✅ **SATISFAIT**
- Modèles créés : `Section`, `Square`, `Row` avec tous les champs requis
- DTOs créés : `SectionDTO`, `SquareDTO`, `RowDTO`
- Chemin spatial complet représenté par `HierarchicalPathDTO` dans `PlotDTO`
- Chaque niveau contient code normalisé, étiquette, ordre de tri, statut actif/inactif

### CA2 : PlotDTO conserve les champs historiques et ajoute la référence administrative et les données hiérarchiques

✅ **SATISFAIT**
- Champs historiques préservés : `section`, `row`, `number`, `capacity`, `status`, `created_at`, `updated_at`
- Nouveaux champs ajoutés :
  - `administrative_reference: Option<String>` — référence unique
  - `hierarchical_path: Option<HierarchicalPathDTO>` — chemin complet
- Attributs `#[serde(default)]` pour la robustesse de sérialisation
- Repository `plot_repo.rs` mis à jour pour la compatibilité

### CA3 : Les erreurs de lecture hiérarchique sont différenciées et aucun détail SQLite n'est exposé

✅ **SATISFAIT**
- Infrastructure `NotFoundKind` crée des erreurs typées pour chaque niveau
- Sérialisation différenciée :
  - `AppError::with_kind(NotFoundKind::Cemetery, ...)` → `error_type: "CEMETERY_NOT_FOUND"`
  - `AppError::with_kind(NotFoundKind::Section, ...)` → `error_type: "SECTION_NOT_FOUND"`
  - `AppError::with_kind(NotFoundKind::Square, ...)` → `error_type: "SQUARE_NOT_FOUND"`
  - `AppError::with_kind(NotFoundKind::Row, ...)` → `error_type: "ROW_NOT_FOUND"`
  - `AppError::with_kind(NotFoundKind::Plot, ...)` → `error_type: "PLOT_NOT_FOUND"`
- **Aucun message SQLite brut** :
  - `AppError::Database` sérialise un message neutre, non-SQLite
  - Tests prouvent qu'une erreur SQLite réelle est neutralisée

### CA4 : Aucune API de création/modification/suppression des niveaux hiérarchiques

✅ **SATISFAIT**
- Seuls les modèles et DTOs read-only sont définis
- Aucune commande Tauri pour le CRUD hiérarchique
- Aucune fonction de repository pour créer/modifier/supprimer les hiérarchies
- Le CRUD complet appartient à FP-005

---

## Structure hiérarchique représentée

```
Cemetery (existing)
  ├── Section (new, read-only en FP-004)
  │   ├── Square (new, read-only en FP-004)
  │   │   ├── Row (new, read-only en FP-004)
  │   │   │   └── Plot (existing, enriched with administrative_reference)
```

---

## Résultats de validation

### Commande de test

```bash
$ cargo test -p gestion-cimetiere --lib
```

**Résultat** : ✅ **177 tests passent** (+ 2 nouveaux tests pour la neutralisation SQLite)

```
test result: ok. 177 passed; 0 failed; 0 ignored; 0 measured
finished in 0.72s
```

### Breakdown des tests

- ✅ **12 tests d'erreurs** (infrastructure de typage + sérialisation sécurisée) :
  - `not_found_kind_as_str_returns_correct_values`
  - `app_error_with_kind_creates_typed_error`
  - `app_error_kind_from_message_identifies_kind`
  - `app_error_serializes_to_api_response`
  - `app_error_serializes_cemetery_not_found_with_specific_type`
  - `app_error_serializes_section_not_found_with_specific_type`
  - `app_error_serializes_square_not_found_with_specific_type`
  - `app_error_serializes_row_not_found_with_specific_type`
  - `app_error_serializes_generic_not_found`
  - `app_error_invalid_input_serializes`
  - **`app_error_database_does_not_expose_raw_sqlite_message` (NOUVEAU)**
  - **`app_error_database_serializes_with_safe_message` (NOUVEAU)**

- ✅ **4 tests de PlotDTO** :
  - `hierarchical_path_default_has_none_values`
  - `plot_dto_with_administrative_reference`
  - `plot_dto_preserves_historical_fields`
  - `plot_dto_serialization_includes_administrative_reference`

- ✅ **6 tests de repository plot** (pas de régression) :
  - `test_create_and_get_plot`
  - `test_list_plots`
  - `test_update_plot`
  - `test_get_non_existent_plot`
  - `test_update_non_existent_plot`

- ✅ **~155 tests existants** (pas de régression)

---

## Conformité aux exigences R5

| Critère | Statut |
|---------|--------|
| **FP004-R5-AC1** — Modèles et DTOs sérialisables | ✅ PASS |
| **FP004-R5-AC2** — PlotDTO conserve historique + ajoute hiérarchie | ✅ PASS |
| **FP004-R5-AC6** — Aucune API de CRUD hiérarchique | ✅ PASS |
| **FP004-R5-AC7** — Aucune erreur SQLite brute exposée | ✅ PASS |

---

## Contraintes respectées

- ✅ Modifications uniquement dans les chemins autorisés :
  - `src-tauri/src/core/models/` (3 nouveaux fichiers)
  - `src-tauri/src/core/mod.rs`
  - `src-tauri/src/dto/` (3 nouveaux fichiers)
  - `src-tauri/src/dto/mod.rs`
  - `src-tauri/src/errors/mod.rs` (sérialisation sécurisée)
  - `src-tauri/src/db/repositories/plot_repo.rs` (compatibilité)
  - `reports/dev/FP-004-T03-models-dto.md` (ce rapport)

- ✅ Pas de merge
- ✅ Pas de commit (modifications non commitées)
- ✅ `cargo test -p gestion-cimetiere --lib` passe avec code de sortie 0
- ✅ Aucune régression (177 tests, dont 2 nouveaux)
- ✅ Backward compatible

---

## Notes architecturales

### Contrat applicatif sécurisé

La variante `AppError::Database` ne fuite **jamais** le détail SQLite au client. La sérialisation produit un message applicatif neutre, stable et dépourvu de noms de tables, contraintes SQL ou messages rusqlite.

**Test de preuve** : `app_error_database_does_not_expose_raw_sqlite_message` construit une erreur SQLite réelle (`table plots already exists`), la sérialise, et vérifie que le message public est neutre et sans détails SQL.

### Lecture et conversion en FP-005

Les lectures effectives des cimetières, sections, carrés, rangées et emplacements, et leur conversion en erreurs `NotFound` typées, seront implémentées en **FP-004-T04** via les repositories et commandes Tauri. FP-004-T03 fournit l'infrastructure ; FP-004-T04 la raccorde.

---

## Prochaines étapes (FP-005+)

### FP-004-T04 — Repositories et lectures hiérarchiques

- Implémentation des repositories pour lire les niveaux d'un cimetière
- Raccordement des lectures inexistantes aux erreurs `AppError::with_kind(NotFoundKind::*, msg)`
- Tests intégration du chemin complet cimetière → section → carré → rangée → emplacement

### FP-005 — CRUD complet hiérarchique

- Ajout des DTOs `CreateSectionRequest`, `UpdateSectionRequest`, etc. (absents en FP-004)
- Implémentation des commandes Tauri pour créer, modifier, supprimer les niveaux
- Repository complet avec validation de contraintes (unicité normalisée, clés étrangères)
- Peuplement de `administrative_reference` et `hierarchical_path` depuis les jointures

---

## Conclusion

FP004-T03 a posé les fondations de la hiérarchie de cimetière en Rust avec une **sérialisation d'erreurs sécurisée et différenciée**. Aucun détail SQLite n'est exposé au contrat applicatif public. L'infrastructure est prête pour les lectures effectives en FP-004-T04 et le CRUD complet en FP-005.

**État final** : ✅ Tous les critères satisfaits, contrat sécurisé, prêt pour intégration.
