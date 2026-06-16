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

5. **Prévention des traversées de répertoires** : Validation que le nom de sauvegarde n'existe pas `..` ou `/`
   - Justification : Sécurité, empêche l'accès hors du répertoire `backups/`
   - Limitation : Impossible de restaurer depuis un chemin absolu

6. **Traitement spécial DB `:memory:`** : Rejet des opérations de sauvegarde en mode debug
   - Justification : DB `:memory:` n'a pas de fichier pour être sauvegardée
   - Impact : Tests limités mais sûrs

## Commandes Tauri exposées

- `create_backup()` → `Result<String, String>` : Crée sauvegarde, retourne chemin
- `list_backups()` → `Result<Vec<String>, String>` : Liste fichiers disponibles, ordre récent d'abord
- `restore_backup(filename: String)` → `Result<(), String>` : Restaure depuis backup, crée sauvegarde de sécurité

## Problèmes connus

Aucun. Tous les tests passent, compilation réussie.

## Résultats des tests

**Unit tests:**
- `services::backup_service::tests::test_backup_filename_format` : ✅ Passing
- `services::backup_service::tests::test_validate_sqlite_header` : ✅ Passing
- **Subtotal unit: 2/2 passing** ✅

**Integration tests:**
- `test_backup_creation` : ✅ Création et vérification fichier
- `test_backup_nonexistent_db` : ✅ Gestion erreur DB inexistante
- `test_list_backups_empty` : ✅ Liste vide au démarrage
- `test_list_backups_multiple` : ✅ Listing avec plusieurs backups, ordre récent d'abord
- `test_restore_backup` : ✅ Restauration et vérification intégrité données
- `test_restore_invalid_backup` : ✅ Gestion erreur backup inexistant
- `test_restore_invalid_sqlite_file` : ✅ Rejet fichier non-SQLite
- `test_path_traversal_prevention` : ✅ Sécurité contre traversée répertoires
- **Subtotal integration: 8/8 passing** ✅

**Full suite:**
- **Total: 68 tests passing, 0 failures** ✅ (54 unit + 8 backup + 6 existants)
- No regressions
- cargo fmt: Clean
- cargo check: Clean
- cargo test: Success

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
