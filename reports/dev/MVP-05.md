# MVP-05 — Définir les contrats API/Tauri et les DTO partagés

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** En cours de définition  
**Dépend de :** MVP-04  

## Objectif

Concevoir les contrats d'échange backend ↔ frontend en définissant les DTOs, modèles de requête/réponse et signatures des commandes Tauri, avec versioning et gestion d'erreur unifiée.

## Tâches clés

- [ ] Définir les structures Rust (DTOs, requêtes, réponses)
- [ ] Établir la gestion centralisée des erreurs
- [ ] Rédiger les signatures des commandes Tauri
- [ ] Documenter les validations côté backend
- [ ] Définir la stratégie de versioning des contrats

## Contrats proposés (MVP)

### Cemeteries

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CemeteryDTO {
    pub id: i64,
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateCemeteryRequest {
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
}
```

### Commands (Tauri)

```rust
#[tauri::command]
pub fn list_cemeteries() -> Result<Vec<CemeteryDTO>, String> {
    // implementation
}

#[tauri::command]
pub fn get_cemetery(id: i64) -> Result<CemeteryDTO, String> {
    // implementation
}

#[tauri::command]
pub fn create_cemetery(req: CreateCemeteryRequest) -> Result<CemeteryDTO, String> {
    // implementation
}

#[tauri::command]
pub fn update_cemetery(id: i64, req: UpdateCemeteryRequest) -> Result<CemeteryDTO, String> {
    // implementation
}

#[tauri::command]
pub fn delete_cemetery(id: i64) -> Result<bool, String> {
    // implementation
}
```

## Fichiers à créer / modifier

- `src-tauri/src/dto/mod.rs`
- `src-tauri/src/dto/cemetery.rs`
- `src-tauri/src/dto/plot.rs`
- `src-tauri/src/dto/concession.rs`
- `src-tauri/src/dto/individual.rs`
- `src-tauri/src/dto/burial.rs`
- `src-tauri/src/commands/mod.rs`
- `src-tauri/src/commands/cemetery.rs`
- `src-tauri/src/commands/plot.rs`
- etc.

## Décisions architecturales

À documenter lors de l'implémentation :
- Stratégie d'erreurs : codes d'erreur standards (HTTP-like ou custom)
- Versioning des contrats : suffixes dans les DTOs ou endpointsv2/
- Validation : côté backend uniquement ou aussi côté frontend
- Pagination : approche (limit/offset, cursor) pour MVP

## Problèmes connus

Aucun pour le moment.

## Résultats des tests

À compléter lors de l'implémentation.

## Prochaines étapes

1. Valider les contrats avec le frontend
2. Lancer MVP-05A : Générer automatiquement les types TypeScript
3. Lancer MVP-10 : Implémenter les commandes Tauri pour cimetières et emplacements
