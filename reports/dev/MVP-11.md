# MVP-11 — Implémenter les commandes Tauri pour concessions, personnes et défunts

**Date:** 2026-06-16
**Agent:** backend
**Statut:** ✅ Terminé
**Dépend de:** MVP-05 ✅, MVP-09 ✅

## Objectif
Implémenter les commandes Tauri réelles pour concessions (concessions), personnes (individuals) et défunts (burials).

## Tâches clés
- [x] Implémenter ConcessionRepository (list, get, create, update)
- [x] Implémenter IndividualRepository (list, get, create, update, search)
- [x] Implémenter BurialRepository (create, get, list_by_concession)
- [x] Implémenter les commandes Tauri pour concessions (4 handlers)
- [x] Implémenter les commandes Tauri pour individuals (5 handlers)
- [x] Implémenter les commandes Tauri pour burials (3 handlers)
- [x] Ajouter les tests unitaires et d'intégration
- [x] Vérifier avec cargo check et cargo test

## Fichiers modifiés / créés
### Repositories
- ✅ src-tauri/src/db/repositories/concession_repo.rs
- ✅ src-tauri/src/db/repositories/individual_repo.rs
- ✅ src-tauri/src/db/repositories/burial_repo.rs
- ✅ src-tauri/src/db/repositories/mod.rs

### Commands
- ✅ src-tauri/src/commands/concession.rs (4 commands)
- ✅ src-tauri/src/commands/individual.rs (5 commands)
- ✅ src-tauri/src/commands/burial.rs (3 commands)
- ✅ src-tauri/src/commands/mod.rs

### Tests
- ✅ src-tauri/tests/integration_concession.rs
- ✅ src-tauri/tests/integration_individual.rs
- ✅ src-tauri/tests/integration_burial.rs

## Résultats des tests
- ✅ cargo check — 0 warnings
- ✅ cargo test --lib — all tests passing
- ✅ cargo test --test integration_* — all passing
- ✅ cargo build — binary builds

## Points d'attention
- FK constraints validated in all repositories
- LIKE search safe (parameterized queries)
- Error handling distinguishes NotFound from Database errors
- Dates in ISO 8601 for cross-platform compatibility
- Update semantics merge partial data (preserve immutable fields)

## Prochaines étapes
1. MVP-12: Créer les écrans dashboard et listes côté frontend
2. MVP-13: Créer les écrans défunts et recherche globale
3. MVP-14: Implémenter le rendu cartographique simple
