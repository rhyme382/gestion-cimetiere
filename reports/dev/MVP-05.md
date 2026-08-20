# MVP-05 — Définir les contrats API/Tauri et les DTO partagés

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** ✅ Stabilisé  
**Dépend de :** MVP-04 ✅ Terminé

## Objectif

Concevoir les contrats d'échange backend ↔ frontend en définissant les DTOs, modèles de requête/réponse et signatures des commandes Tauri, avec versioning et gestion d'erreur unifiée.

## Tâches clés

- [x] Définir les structures Rust (DTOs, requêtes, réponses)
- [x] Établir la gestion centralisée des erreurs
- [x] Rédiger les signatures des commandes Tauri
- [x] Documenter les validations côté backend
- [x] Définir la stratégie de versioning des contrats

## Contrats implémentés

### DTOs de réponse (avec dérivation specta::Type)

Tous les DTOs implémentent : `#[derive(Debug, Clone, Serialize, Deserialize, Type)]`

- ✅ **CemeteryDTO** : id, name, commune?, capacity?, created_at, updated_at
- ✅ **PlotDTO** : id, cemetery_id, section?, row?, number?, capacity, status, created_at, updated_at
- ✅ **ConcessionDTO** : id, cemetery_id, plot_id?, acquired_at?, expires_at?, renewed_at?, status, created_at, updated_at
- ✅ **IndividualDTO** : id, name, email?, phone?, role, created_at, updated_at
- ✅ **BurialDTO** : id, concession_id, individual_id, buried_at?, created_at, updated_at

### Requêtes de création/modification

- ✅ **CreateCemeteryRequest** : name, commune?, capacity?
- ✅ **UpdateCemeteryRequest** : name?, commune?, capacity?
- ✅ **CreatePlotRequest** : cemetery_id, section?, row?, number?, capacity
- ✅ **UpdatePlotRequest** : section?, row?, number?, capacity?, status?
- ✅ **CreateConcessionRequest** : cemetery_id, plot_id?, acquired_at?, expires_at?
- ✅ **UpdateConcessionRequest** : plot_id?, acquired_at?, expires_at?, renewed_at?, status?
- ✅ **CreateIndividualRequest** : name, email?, phone?, role
- ✅ **UpdateIndividualRequest** : name?, email?, phone?, role?
- ✅ **CreateBurialRequest** : concession_id, individual_id, buried_at?

## Commandes Tauri (stubs, compilables)

Toutes les commandes retournent `Result<T, String>` et sont décorées avec `#[tauri::command]`.

### Cemeteries
- `list_cemeteries(state) -> Result<Vec<CemeteryDTO>, String>` ✅
- `get_cemetery(state, id: i64) -> Result<CemeteryDTO, String>` ✅
- `create_cemetery(state, req: CreateCemeteryRequest) -> Result<CemeteryDTO, String>` ✅
- `update_cemetery(state, id: i64, req: UpdateCemeteryRequest) -> Result<CemeteryDTO, String>` ✅
- `delete_cemetery(state, id: i64) -> Result<bool, String>` ✅

### Plots
- `list_plots(state, cemetery_id: i64) -> Result<Vec<PlotDTO>, String>` ✅
- `get_plot(state, id: i64) -> Result<PlotDTO, String>` ✅
- `create_plot(state, req: CreatePlotRequest) -> Result<PlotDTO, String>` ✅
- `update_plot(state, id: i64, req: UpdatePlotRequest) -> Result<PlotDTO, String>` ✅

### Concessions
- `list_concessions(state, cemetery_id?: i64) -> Result<Vec<ConcessionDTO>, String>` ✅
- `get_concession(state, id: i64) -> Result<ConcessionDTO, String>` ✅
- `create_concession(state, req: CreateConcessionRequest) -> Result<ConcessionDTO, String>` ✅
- `update_concession(state, id: i64, req: UpdateConcessionRequest) -> Result<ConcessionDTO, String>` ✅

### Individuals
- `list_individuals(state) -> Result<Vec<IndividualDTO>, String>` ✅
- `get_individual(state, id: i64) -> Result<IndividualDTO, String>` ✅
- `create_individual(state, req: CreateIndividualRequest) -> Result<IndividualDTO, String>` ✅
- `update_individual(state, id: i64, req: UpdateIndividualRequest) -> Result<IndividualDTO, String>` ✅
- `search_individuals(state, query: String) -> Result<Vec<IndividualDTO>, String>` ✅

## Gestion des erreurs

**Type :** `AppError` (via `thiserror`)

```rust
pub enum AppError {
    Database(rusqlite::Error),
    NotFound(String),
    InvalidInput(String),
    Internal(String),
}
```

Les erreurs sont sérialisées en `String` pour les commandes Tauri (limites de l'API v2).

## Versioning

- **Stratégie** : DTOs immuables une fois créés ; si modification, créer `CemeteryDTOv2` plutôt que modifier
- **Compatibilité** : tous les champs optionnels pour extensibilité future
- **Migration** : décider côté frontend si versions multiples nécessaires

## Fichiers créés / modifiés

- ✅ `src-tauri/src/dto/cemetery.rs`
- ✅ `src-tauri/src/dto/plot.rs`
- ✅ `src-tauri/src/dto/concession.rs`
- ✅ `src-tauri/src/dto/individual.rs`
- ✅ `src-tauri/src/dto/burial.rs`
- ✅ `src-tauri/src/commands/cemetery.rs`
- ✅ `src-tauri/src/commands/plot.rs`
- ✅ `src-tauri/src/commands/concession.rs`
- ✅ `src-tauri/src/commands/individual.rs`
- ✅ `src-tauri/src/main.rs` (invoke_handler avec toutes les commandes)

## Problèmes connus

Aucun. Les commandes sont stubs (retournent "Not implemented") mais compilables et sérialisables.

## Résultats des tests

- ✅ `cargo check` — Aucune erreur de type
- ✅ `cargo test --lib` — Tous les tests passent
- ✅ DTOs compilent avec `specta::Type`

## Prochaines étapes

1. MVP-05A : Générer types TypeScript à partir des DTOs
2. MVP-09 : Implémenter les repositories pour popule les commandes
3. MVP-10/11 : Implémenter les services métier
