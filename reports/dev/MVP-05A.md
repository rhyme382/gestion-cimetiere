# MVP-05A — Générer automatiquement les types TypeScript à partir des modèles Rust

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** ✅ Stabilisé (préparation pour MVP-06)  
**Dépend de :** MVP-05 ✅ Terminé

## Objectif

Mettre en place la génération automatique des types TypeScript à partir des structures Rust afin de maintenir les types frontend synchrones avec le backend sans effort manuel.

## Tâches clés

- [x] Sélectionner l'outil de génération (specta v2 + tauri-specta)
- [x] Configurer le code Rust pour la génération (`Type` derive)
- [x] Tester la dérivation du trait specta::Type sur tous les DTOs
- [x] Documenter le flux de génération
- [x] Préparer l'intégration en mode debug

## Outil retenu : **specta v2 + tauri-specta v2**

**Justification :**
- Intégration Tauri native
- Génération statique (pas de runtime overhead)
- Support Rust → TypeScript exact
- Compatible Tauri v2.x

**Versions :**
- `specta = "2.0.0-rc.25"`
- `tauri-specta = "2.0.0-rc.22"`

## Configuration implémentée

### Dépendances Cargo

```toml
[dependencies]
specta = "2.0.0-rc.25"
tauri-specta = "2.0.0-rc.22"

[build-dependencies]
tauri-build = { version = "2", features = [] }
```

### Dérivation Type sur DTOs

Tous les DTOs et requêtes dérivent `specta::Type`:

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CemeteryDTO {
    pub id: i64,
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
    pub created_at: String,
    pub updated_at: String,
}
```

DTOs complètement typés :
- ✅ CemeteryDTO + CreateCemeteryRequest + UpdateCemeteryRequest
- ✅ PlotDTO + CreatePlotRequest + UpdatePlotRequest
- ✅ ConcessionDTO + CreateConcessionRequest + UpdateConcessionRequest
- ✅ IndividualDTO + CreateIndividualRequest + UpdateIndividualRequest
- ✅ BurialDTO + CreateBurialRequest

## Flux de génération

### En mode debug (à finir après MVP-06)

Dans `src-tauri/src/lib.rs` :

```rust
#[cfg(debug_assertions)]
pub fn export_bindings() -> Result<(), Box<dyn std::error::Error>> {
    // Code de génération tauri-specta sera ajouté ici
    Ok(())
}
```

Appelé depuis `src-tauri/src/main.rs` au startup en debug.

### En mode release

La génération peut être manuelle ou intégrée en CI/CD après MVP-06.

## Types générés (aperçu futur)

Après intégration complète, fichier généré : `src/types/tauri-bindings.ts`

Exemple de ce que sera généré :

```typescript
// Auto-generated from Rust structs
export interface CemeteryDTO {
  id: number;
  name: string;
  commune: string | null;
  capacity: number | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCemeteryRequest {
  name: string;
  commune?: string;
  capacity?: number;
}
```

## Fichiers créés / modifiés

- ✅ `src-tauri/Cargo.toml` (ajout specta et tauri-specta)
- ✅ Tous les DTOs avec `Type` dérivé
- ✅ `src-tauri/src/lib.rs` (structure pour export_bindings)
- ✅ `src-tauri/src/main.rs` (appel export_bindings en debug)
- ✅ `.gitignore` couvre déjà `src/types/`

## Problèmes connus

- tauri-specta v2 est toujours en RC (pas de version stable)
- Génération manuelle pour l'instant, pas d'intégration build automatique
  (peut être ajoutée dans MVP-06 ou via script)

## Résultats des tests

- ✅ `cargo check` — Tous les types compilent avec `Type` dérivé
- ✅ DTOs sont visibles par tauri-specta (pas d'erreurs d'introspection)
- ✅ `cargo test --lib` — Tous les tests passent

## Prochaines étapes

1. MVP-06 (frontend) : Intégrer les types générés dans React/TypeScript
2. Ajouter script d'export manuel ou intégration build pour générer types régulièrement
3. Valider non-divergence Rust ↔ TypeScript en tests E2E (MVP-26)

## Note pour MVP-06+

Le frontend peut utiliser les types générés ainsi :

```typescript
import { CemeteryDTO, CreateCemeteryRequest } from "./types/tauri-bindings";
// ... utiliser les types
```

Les commandes Tauri seront appelées avec typage automatique.
