# MVP-05A — Générer automatiquement les types TypeScript à partir des modèles Rust

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** En cours de définition  
**Dépend de :** MVP-05  

## Objectif

Mettre en place la génération automatique des types TypeScript à partir des structures Rust afin de maintenir les types frontend synchrones avec le backend sans effort manuel.

## Tâches clés

- [ ] Sélectionner l'outil de génération (specta, tsify, serde-wasm-bindgen, etc.)
- [ ] Configurer le code Rust pour la génération (derive attributes, annotations)
- [ ] Générer les types TypeScript initiaux
- [ ] Automatiser la génération en CI/CD (pré-commit ou build)
- [ ] Documenter le flux et les conventions

## Outil proposé : **specta** (recommandé)

**Raison :** Intégration Tauri native, génération statique (pas de runtime), support Rust → TS exact.

### Configuration proposée

```toml
# src-tauri/Cargo.toml
[dependencies]
specta = { version = "1.0", features = ["derive", "serde"] }
serde = { version = "1", features = ["derive"] }

[dev-dependencies]
```

### Code exemple

```rust
// src-tauri/src/dto/cemetery.rs
use specta::Type;
use serde::{Deserialize, Serialize};

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

### Générateur (build.rs ou CLI)

```bash
# Package : specta-typescript
cargo install specta-cli

specta export \
  --ts \
  --out-dir src/types \
  --namespace Cemetery \
  src-tauri/src/dto/cemetery.rs
```

## Fichiers à créer / modifier

- `src-tauri/build.rs` (ou script de pré-build)
- `src-tauri/src/dto/mod.rs` (attributs derive)
- `.github/workflows/ci.yml` (ou make install-types)
- `src/types/` (dossier généré, dans .gitignore)
- Documentation : `guides/TYPES_GENERATION.md`

## Décisions architecturales

À documenter lors de l'implémentation :
- Outil retenu et justification
- Déclencheur de génération (build, pré-commit, hook CI)
- Stockage des types générés (dossier, chemin)
- Convention de nommage des fichiers générés

## Problèmes connus

Aucun pour le moment.

## Résultats des tests

À compléter lors de l'implémentation :
- Les types générés correspondent aux structures Rust
- La génération est automatisée et fiable
- Aucune divergence Rust ↔ TypeScript

## Prochaines étapes

1. Valider le flux de génération avec le frontend
2. Lancer MVP-06 : Mettre en place la base de composants UI et le shell de navigation
3. Lancer MVP-10 : Implémenter les commandes Tauri (utilisant les types générés)
