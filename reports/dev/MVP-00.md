# MVP-00 — Stabiliser la structure du dépôt et les conventions de modules

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** ✅ Stabilisé  

## Objectif

Nettoyer et structurer le dépôt pour accueillir le développement MVP de manière robuste et maintenable.

## Tâches clés

- [x] Organiser l'arborescence de modules Rust/Tauri
- [x] Définir les conventions de nommage et d'organisation du code
- [x] Mettre en place `.gitignore`, `.editorconfig` et les outils de linting
- [x] Préparer les répertoires de migrations, tests et documentation
- [x] Créer le squelette de `Cargo.toml` avec dépendances MVP

## Fichiers modifiés / créés

- ✅ `Cargo.toml` (workspace root)
- ✅ `src-tauri/Cargo.toml` (backend avec dépendances Tauri v2)
- ✅ `.editorconfig` (conventions d'indentation et style)
- ✅ `.gitignore` (déjà existant, conforme)
- ✅ Structure créée : `src-tauri/src/{core,commands,services,db,models,errors}`
- ✅ `build.rs` (Tauri build script)

## Décisions architecturales

- **Workspace Cargo** : oui, avec `src-tauri` comme crate principal
- **Tauri v2** : versioning explicite pour stabilité
- **Pattern de modules** : hiérarchie claire (core → models/services, db → connection/migrations/repositories, commands, dto)
- **Conventions** : snake_case pour modules/variables, PascalCase pour structs/enums, indentation 4 espaces Rust
- **Linting** : Rust defaults (rustfmt, clippy via cargo check)

## Problèmes connus

Aucun — la structure est opérationnelle et compilable.

## Résultats des tests

- `cargo check` ✅ Succès
- Migration SQLite ✅ Succès (structure créée, contraintes intégrées)
- Dépendances ✅ Résolues (Tauri v2.11.2, rusqlite 0.31, specta 2.0.0-rc.25)

## Prochaines étapes

1. MVP-01 : Architecture applicative du workspace desktop (en cours)
2. MVP-04 : Implémenter les migrations et les modèles métier
3. MVP-05 : Créer les commandes Tauri exécutables
