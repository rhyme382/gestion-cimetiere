# MVP-01 — Définir l'architecture applicative du workspace desktop

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** En cours de définition  
**Dépend de :** MVP-00  

## Objectif

Poser les fondations architecturales du workspace Tauri/Rust en définissant l'organisation des crates, les patterns de dépendances intra-projet et la structure des modules métier.

## Tâches clés

- [ ] Définir l'organisation des crates (backend, core, commands, etc.)
- [ ] Établir les patterns de dépendances intra-projet
- [ ] Créer le squelette des modules métier (store, services, repositories)
- [ ] Documenter les principes de layering et de responsabilité
- [ ] Valider la compatibilité avec les contrats frontend (MVP-05A)

## Architecture proposée

```
src-tauri/
├── src/
│   ├── main.rs              # Point d'entrée
│   ├── core/                # Domaine métier
│   │   ├── models/          # Entités métier
│   │   ├── services/        # Logique métier
│   │   └── errors/          # Gestion d'erreurs
│   ├── db/                  # Persistance
│   │   ├── connection.rs
│   │   ├── migrations/
│   │   └── repositories/
│   ├── commands/            # Interface Tauri
│   │   ├── cemeteries.rs
│   │   ├── plots.rs
│   │   ├── concessions.rs
│   │   └── ...
│   └── dto/                 # Contrats ↔ Frontend
├── Cargo.toml
└── migrations/              # Schéma SQLite
```

## Fichiers à modifier / créer

- `src-tauri/src/main.rs`
- `src-tauri/src/core/mod.rs`
- `src-tauri/src/db/mod.rs`
- `src-tauri/src/commands/mod.rs`
- `src-tauri/src/dto/mod.rs`
- Structure de modules détaillée

## Décisions architecturales

À documenter lors de l'implémentation :
- Pattern d'injection de dépendances (si applicable)
- Gestion des transactions et de la cohérence
- Stratégie de validation et d'erreurs
- Approche pour les services métier (traits vs structures)

## Problèmes connus

Aucun pour le moment.

## Résultats des tests

À compléter lors de l'implémentation.

## Prochaines étapes

1. Valider l'architecture avec les agents frontend et mapping
2. Lancer MVP-04 : Définir le schéma SQLite MVP et les entités cœur
3. Lancer MVP-03 (QA) : Définir la stratégie de tests du MVP
