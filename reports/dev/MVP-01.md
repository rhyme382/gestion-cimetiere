# MVP-01 — Définir l'architecture applicative du workspace desktop

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** ✅ Stabilisé  
**Dépend de :** MVP-00 ✅ Terminé

## Objectif

Poser les fondations architecturales du workspace Tauri/Rust en définissant l'organisation des crates, les patterns de dépendances intra-projet et la structure des modules métier.

## Tâches clés

- [x] Définir l'organisation des crates (backend, core, commands, etc.)
- [x] Établir les patterns de dépendances intra-projet
- [x] Créer le squelette des modules métier (store, services, repositories)
- [x] Documenter les principes de layering et de responsabilité
- [x] Valider la compatibilité avec les contrats frontend (MVP-05A)

## Architecture implémentée

```
src-tauri/src/
├── main.rs              # Point d'entrée Tauri
├── lib.rs               # Module root + exports
├── errors/              # Gestion d'erreurs centralisée
│   └── mod.rs          # AppError avec thiserror
├── core/                # Domaine métier
│   ├── mod.rs
│   ├── models/         # Entités (Cemetery, Plot, etc.)
│   │   ├── mod.rs
│   │   ├── cemetery.rs
│   │   ├── plot.rs
│   │   ├── concession.rs
│   │   ├── individual.rs
│   │   └── burial.rs
│   └── services/       # Logique métier
│       ├── mod.rs
│       └── cemetery_service.rs (stub, à implémenter)
├── db/                  # Persistance
│   ├── mod.rs
│   ├── connection.rs   # Gestion SQLite
│   ├── migrations.rs   # Exécution des migrations
│   └── repositories/   # Accès données
│       ├── mod.rs
│       └── cemetery_repo.rs (stub)
├── dto/                 # Contrats ↔ Frontend
│   ├── mod.rs
│   ├── cemetery.rs
│   ├── plot.rs
│   ├── concession.rs
│   ├── individual.rs
│   └── burial.rs
└── commands/            # Interface Tauri
    ├── mod.rs
    ├── cemetery.rs      # list, get, create, update, delete
    ├── plot.rs
    ├── concession.rs
    └── individual.rs
```

## Fichiers modifiés / créés

- ✅ `src-tauri/src/lib.rs` (exports, init_app)
- ✅ `src-tauri/src/main.rs` (Tauri entry, DB init, command handler)
- ✅ Modules core, db, dto, commands, errors (tous créés et compilables)
- ✅ `src-tauri/src/db/connection.rs` (avec tests de connexion)
- ✅ `src-tauri/src/db/migrations.rs` (avec tests de migrations)

## Décisions architecturales

- **Layering** : core (métier) → db (données) → commands (API Tauri)
- **Erreurs** : `AppError` centralisée via `thiserror`, sérialisable en `String` pour Tauri
- **State** : `Mutex<Connection>` gérée par Tauri `.manage()`
- **DTOs** : séparés des modèles DB, avec dérivation `specta::Type` pour génération TS
- **Services** : stubs en place, logique à implémenter dans MVP-09+
- **Repositories** : stubs en place, logique à implémenter dans MVP-09+
- **Tests** : tests unitaires en place pour migrations, connexion SQLite

## Problèmes connus

Aucun — architecture compilable et testée.

## Résultats des tests

- `cargo test --lib` ✅ 3/3 tests passent
  - `test_init_db_in_memory` ✅
  - `test_foreign_keys_enabled` ✅
  - `test_migrations_run` ✅
- `cargo check` ✅ Aucune erreur
- Compilation totale ✅ Succès

## Prochaines étapes

1. MVP-04 : Implémenter les migrations initiales et les fixtures (en cours)
2. MVP-05 : Implémenter les commandes Tauri fonctionnelles
3. MVP-09 : Implémenter les services et repositories métier
