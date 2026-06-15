# MVP-00 — Stabiliser la structure du dépôt et les conventions de modules

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** En cours de définition  

## Objectif

Nettoyer et structurer le dépôt pour accueillir le développement MVP de manière robuste et maintenable.

## Tâches clés

- [ ] Organiser l'arborescence de modules Rust/Tauri
- [ ] Définir les conventions de nommage et d'organisation du code
- [ ] Mettre en place `.gitignore`, `.editorconfig` et les outils de linting
- [ ] Préparer les répertoires de migrations, tests et documentation
- [ ] Créer le squelette de `Cargo.toml` avec dépendances MVP

## Fichiers à modifier / créer

- `Cargo.toml` (workspace root)
- `src-tauri/Cargo.toml` (backend)
- `.gitignore`
- `.editorconfig`
- `src-tauri/rustfmt.toml`
- Structure : `src-tauri/src/{core,commands,services,db,models,errors}`

## Décisions architecturales

À documenter lors de l'implémentation :
- Pattern de modules et organisation des crates
- Conventions de nommage (fonctions, structures, constantes)
- Choix de linter et de formatter (rustfmt, clippy)

## Problèmes connus

Aucun pour le moment.

## Résultats des tests

À compléter lors de l'implémentation.

## Prochaines étapes

1. Valider l'organisation de l'arborescence
2. Lancer MVP-01 : Définir l'architecture applicative du workspace desktop
