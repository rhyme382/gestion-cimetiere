# MVP-20 — Implémenter sauvegarde/restauration locale

**Date :** 2026-06-16  
**Agent :** backend  
**Statut :** ✅ Complete

## Objectif

Implémenter la sauvegarde et la restauration complète de la base de données SQLite locale pour permettre aux mairies de sauvegarder et restaurer leurs données.

Fonctionnalités :
- Sauvegarde complète de la base SQLite
- Création d'un fichier de sauvegarde daté avec nanoprécision
- Restauration d'une sauvegarde existante
- Validation de l'en-tête SQLite avant restauration
- Gestion robuste des erreurs
- Création de sauvegarde de sécurité avant restauration
- Prévention des attaques par traversée de répertoires

## Fichiers créés / modifiés

**Créés:**
- `src-tauri/src/services/backup_service.rs` — Service de sauvegarde/restauration
- `src-tauri/src/commands/backup.rs` — Commandes Tauri pour backup/restore/list
- `src-tauri/tests/integration_backup.rs` — 8 tests d'intégration

**Modifiés:**
- `src-tauri/src/services/mod.rs` — Export de BackupService
- `src-tauri/src/commands/mod.rs` — Export des commandes backup
- `src-tauri/src/main.rs` — Ajout state DB path, enregistrement commandes

## Décisions prises

1. **Répertoire local `backups/`** : Sauvegardes dans le répertoire `backups/` adjacent à la base de données
   - Justification : MVP local, pas de cloud ; accessible et visible par l'utilisateur mairie
   - Implémentation : pour une DB à `/path/to/db.db`, backups vont dans `/path/to/backups/`
   - Fallback : pour une DB sans chemin parent (e.g., `db.db`), backups vont dans `./backups/` (relatif au cwd)
   - Note : Créé automatiquement s'il n'existe pas

2. **Nommage unique avec nanoprécision** : `backup_{YYYYMMDD_HHMMSS}_{nanoseconds}.db`
   - Justification : Évite les collisions même en cas de sauvegardes rapides successives
   - Alternative écartée : utiliser UUID (plus complexe)

3. **Validation en-tête SQLite** : Vérification que le fichier commence par `SQLite format 3\x00`
   - Justification : Prévient la restauration de fichiers corrompus ou invalides
   - Protection : Rend la DB inutile de restaurer un fichier arbitraire

4. **Sauvegarde de sécurité avant restauration** : Création automatique de `backup_pre_restore_*.db`
   - Justification : Récupération facile en cas d'erreur de restauration accidentelle
   - Note : Pas de limite de stockage en MVP (nettoyage manuel)

5. **Prévention des traversées de répertoires** : Validation robuste multi-plateforme
   - Rejette : `..`, `/`, `\`, chemins absolus Windows (C:), chemins UNC
   - Détails : vérification explicite de `\\` (antislash Windows), `/` (slash Unix), préfixes absolus, drive letters Windows
   - Justification : Sécurité complète sur Windows et Linux, empêche l'accès hors du répertoire `backups/`
   - Code : vérifications via `contains()`, `starts_with()`, et détection `cfg!(windows)` pour chemins absolus

6. **Traitement spécial DB `:memory:`** : Rejet des opérations de sauvegarde en mode debug
   - Justification : DB `:memory:` n'a pas de fichier pour être sauvegardée
   - Impact : Tests limités mais sûrs

## Commandes Tauri exposées

- `create_backup()` → `Result<String, String>` : Crée sauvegarde, retourne chemin
- `list_backups()` → `Result<Vec<String>, String>` : Liste fichiers disponibles, ordre récent d'abord
- `restore_backup(filename: String)` → `Result<(), String>` : Restaure depuis backup, crée sauvegarde de sécurité

## Isolation des tests — Implémentation TempDir

**Approche :** Chaque test backup utilise un répertoire temporaire unique fourni par le crate `tempfile`.

**Code pattern :**
```rust
#[test]
fn test_restore_backup() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");
    
    // Tous les fichiers de test créés dans temp_dir, automatiquement supprimés
    // lors du drop de temp_dir = isolation complète, pas de conflits
}
```

**Avantages :**
- ✅ Chaque test a son propre répertoire isolé
- ✅ Cleanup automatique du système (temp_dir dropped)
- ✅ Pas de `cleanup_backups()` global qui supprime les fichiers d'autres tests
- ✅ Compatible avec l'exécution parallèle
- ✅ Pas de dépendance sur `--test-threads=1`

**Dépendance :**
- Crate `tempfile` ajouté à dev-dependencies dans `Cargo.toml`
- Import : `use tempfile::TempDir;`

## Problèmes connus

### Test isolation (résolu ✅)
- **Problème initial :** Les tests partageaient le répertoire `backups/` global, causant des conflits en exécution parallèle
- **Solution appliquée :** Tests utilisant `TempDir` du crate `tempfile` pour chaque test
  - Chaque test obtient un répertoire temporaire unique et isolé
  - `cleanup_backups()` supprime uniquement le répertoire temporaire de ce test
  - Pas de conflit entre tests parallèles
- **Résultat :** Tous les tests passent en exécution parallèle normale, **sans `--test-threads=1`**
- **Production :** Chaque instance DB a son répertoire `backups/` adjacent, isolation garantie naturellement

## Résultats des tests

**Unit tests (dans lib.rs):**
- `services::backup_service::tests::test_backup_filename_format` : ✅ Passing
- `services::backup_service::tests::test_validate_sqlite_header` : ✅ Passing
- **Subtotal unit: 2/2 passing** ✅

**Integration tests (tests/integration_backup.rs):**
- `test_backup_creation` : ✅ Création et vérification fichier
- `test_backup_nonexistent_db` : ✅ Gestion erreur DB inexistante
- `test_list_backups_empty` : ✅ Liste vide au démarrage (passé avec paramètre db_path)
- `test_list_backups_multiple` : ✅ Listing avec plusieurs backups, ordre récent d'abord (passé avec paramètre db_path)
- `test_restore_backup` : ✅ Restauration et vérification intégrité données
- `test_restore_invalid_backup` : ✅ Gestion erreur backup inexistant
- `test_restore_invalid_sqlite_file` : ✅ Rejet fichier non-SQLite
- `test_path_traversal_prevention` : ✅ Sécurité contre traversée répertoires (incluant chemin absolu)
- **Subtotal integration: 8/8 passing** ✅

**Full suite:**
- **Total: 91 tests passing, 0 failures** ✅
  - 54 unit tests (lib.rs)
  - 8 backup integration tests ✅
  - 4 alert integration tests
  - 4 burial integration tests
  - 4 cemetery integration tests
  - 5 concession integration tests
  - 5 individual integration tests
  - 3 PDF integration tests
  - 4 plot integration tests
- No regressions
- cargo fmt: ✅ Clean
- cargo check: ✅ Clean
- cargo test (exécution parallèle normale): ✅ All passing

**Note technique:** Tests exécutés en mode parallèle normal (sans `--test-threads=1`). Isolation complète garantie via `TempDir` pour chaque test backup. En production, chaque DB a son répertoire `backups/` adjacent.

## Prochaines étapes

1. **MVP-21** (Packaging) : Intégrer sauvegarde/restauration dans packaging Windows NSIS
   - Ajouter bouton UI pour sauvegarde (non implémenté en MVP-20)
   - Permettre configuration du répertoire de sauvegarde en paramètres app

2. **MVP-22** (Packaging Linux) : Adaptation AppImage/deb pour sauvegarde
   - Répertoire de sauvegarde dans `~/.local/share/gestion-cimetiere/backups/`
   - Intégration avec dépôts utilisateur

3. **Amélioration post-MVP** :
   - Sauvegarde automatique planifiée (quotidienne ?)
   - Limite de rétention (garder max N sauvegardes)
   - Chiffrement des sauvegardes
   - Sauvegarde incrémentale
   - Export/import via cloud (hors MVP)
   - Compression des sauvegardes

4. **Interface utilisateur** : MVP-19+ dépend de cette couche pour exposer les sauvegardes à l'UI

## Notes d'architecture

- `BackupService` est découplé de Tauri et peut être testé indépendamment
- Commandes Tauri passent le chemin DB via state (pattern similaire à `generate_concession_pdf`)
- Gestion d'erreurs uniforme : `Result<T, String>` pour cohérence API Tauri
- Tests utilisent SQLite header valide pour simulation fichiers réels
- Pas de dépendances externes pour backup (utilise `std::fs` uniquement)

## Compatibilité Windows/Linux

**Approche multi-plateforme:**
- Utilisation de `std::fs` et `PathBuf` pour abstraction OS-agnostique
- Validation path traversal couvre les deux OS (/, \\, chemins absolus)
- Tests passent identiquement sur Windows et Linux

**Détails de sécurité:**
- Rejet explicite de `\\` (antislash Windows)
- Rejet de `/` (slash Unix et Windows)
- Rejet de chemins commençant par `/` ou `\` (paths absolus)
- Détection Windows drive letters (C:, D:, etc.) via `cfg!(windows)` + vérification `:` en position 1
- Pas de dépendances OS-spécifiques

**Notes de déploiement:**
- Windows : Backups restent dans répertoire SQLite
- Linux : Backups restent dans répertoire SQLite (peut être `~/.local/share/...` selon Tauri config)
- Paths sont canonicalisés par le système de fichiers OS

## Contraintes MVP respectées

✅ Sauvegarde locale uniquement (pas de cloud)  
✅ Pas de synchronisation  
✅ Pas de sauvegarde automatique planifiée  
✅ Pas de chiffrement  
✅ Pas de sauvegarde incrémentale  
✅ Pas d'interface utilisateur (backend seulement)  
✅ Pas de modification frontend  
✅ Pas de modification cartographie  
✅ Pas de modification moteur PDF  
