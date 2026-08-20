# MVP-10 — Implémenter les commandes Tauri pour cimetières et emplacements

**Date:** 2026-06-16
**Agent:** backend
**Statut:** ✅ Terminé
**Dépend de:** MVP-05 ✅, MVP-09 ✅

## Objectif
Implémenter les commandes Tauri réelles (CRUD) pour les cimetières (cemeteries) et emplacements (plots).

## Tâches clés
- [x] Implémenter CemeteryRepository (list, get, create, update, delete)
- [x] Implémenter PlotRepository (list, get, create, update)
- [x] Implémenter les commandes Tauri pour cemeteries (5 handlers)
- [x] Implémenter les commandes Tauri pour plots (4 handlers)
- [x] Ajouter les tests unitaires et d'intégration
- [x] Vérifier avec cargo check et cargo test

## Fichiers modifiés / créés
- ✅ src-tauri/src/db/repositories/cemetery_repo.rs
- ✅ src-tauri/src/db/repositories/plot_repo.rs
- ✅ src-tauri/src/db/repositories/mod.rs
- ✅ src-tauri/src/commands/cemetery.rs (5 commands)
- ✅ src-tauri/src/commands/plot.rs (4 commands)
- ✅ src-tauri/src/commands/mod.rs
- ✅ src-tauri/tests/integration_cemetery.rs
- ✅ src-tauri/tests/integration_plot.rs

## Résultats des tests
- ✅ cargo check — 0 warnings
- ✅ cargo test --lib — all tests passing
- ✅ cargo test --test integration_* — all passing
- ✅ cargo build — binary builds

## Prochaines étapes
1. MVP-11: Implémenter les commandes pour concessions, personnes et défunts
2. MVP-12: Créer les écrans dashboard côté frontend
