# TASK-PILOT-001 : Correction des tests de diagnostic SQLite

**Date** : 2026-07-13  
**Branche** : `autodev/TASK-PILOT-001`  
**Statut** : ✅ Complété

## Contexte

Le reviewer a identifié que le chemin d'échec SQLite dans la logique de diagnostic n'était pas réellement testé au niveau du comportement. Les tests existants validaient uniquement la construction des DTOs d'erreur, sans vérifier que le diagnostic gère une véritable erreur SQLite gracieusement.

## Changements réalisés

### Fichier : `src-tauri/src/commands/diagnostic.rs`

#### Nouveaux tests ajoutés

1. **`test_diagnostic_with_temp_file_db`**
   - Crée une base de données temporaire sur le disque (non en mémoire)
   - Valide que `check_sqlite_health()` fonctionne correctement avec une BD réelle
   - Teste le chemin nominal avec une vraie BD

2. **`test_diagnostic_sqlite_error_behavior`**
   - Simule un scénario d'erreur SQLite en rendant le répertoire de la BD inaccessible
   - Sur Unix : modifie les permissions du répertoire à `0o000`
   - Valide que `init_db()` échoue gracieusement quand l'accès est refusé
   - Restaure les permissions après le test pour le cleanup
   - Vérifie que le diagnostic peut gérer une erreur d'accès à la BD

3. **`test_diagnostic_sqlite_error_message_structure`**
   - Valide que le DTO d'erreur contient une structure de message cohérente
   - Teste que les erreurs SQLite produisent un message structuré sans panique
   - Vérifie l'intégrité du message d'erreur qui combine le préfixe standard et les détails de l'erreur

#### Tests conservés

Tous les tests existants ont été conservés et continuent de passer :
- `test_diagnostic_healthy_with_in_memory_db`
- `test_diagnostic_returns_app_version`
- `test_diagnostic_dto_healthy`
- `test_diagnostic_dto_sqlite_error`

## Vérifications exécutées

```bash
# Tous les tests du package
cargo test -p gestion-cimetiere
Result: ✅ 61 tests passed (0 failed)

# Vérification du formatage
cargo fmt --check --manifest-path src-tauri/Cargo.toml
Result: ✅ Code formaté correctement
```

## Comportement validé

✅ BD temporaire réelle : le diagnostic fonctionne correctement  
✅ Erreur d'accès à la BD : gérée gracieusement sans panique  
✅ Structure du DTO d'erreur : cohérente et contient tous les détails  
✅ Message d'erreur : combines le contexte et les détails d'erreur SQLite  
✅ Pas de régressions : tous les tests existants continuent de passer

## Notes techniques

- Les tests utilisent `tempfile::tempdir()` pour créer des bases de données temporaires
- Le test de permissions est conditionnel sur Unix (`#[cfg(unix)]`) pour éviter les problèmes sur Windows
- Tous les tests inclus permettent de détecter les régressions futures du chemin d'erreur SQLite
