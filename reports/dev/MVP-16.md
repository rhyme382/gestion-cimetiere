# MVP-16 — Implémenter les alertes d'échéance MVP

**Date :** 2026-06-16  
**Agent :** backend  
**Statut :** ✅ Complete

## Objectif

Implémenter un moteur d'alertes qui détecte les concessions approchant de l'expiration ou déjà expirées, avec calcul automatique des seuils configurables et exposition via deux commandes Tauri : `list_alerts()` et `get_alert_summary()`.

## Fichiers créés / modifiés

**Créés:**
- `src-tauri/src/dto/alert.rs` — AlertType enum (Critical/Warning/Info), AlertDTO, AlertSummaryDTO
- `src-tauri/src/db/repositories/alert_repo.rs` — Couche repository avec CRUD + agrégations
- `src-tauri/src/services/alert_service.rs` — Logique métier pour calcul d'alertes basé sur seuils
- `src-tauri/src/commands/alert.rs` — 4 handlers Tauri (list_alerts, get_alert_summary, refresh_alerts, acknowledge_alert)
- `src-tauri/migrations/0006_create_alerts_table.sql` — Migration de la table alerts
- `src-tauri/tests/integration_alert.rs` — 4 tests d'intégration complets

**Modifiés:**
- `src-tauri/src/dto/mod.rs` — Export des types AlertDTO, AlertSummaryDTO, AlertType
- `src-tauri/src/db/repositories/mod.rs` — Export du repository AlertRepository
- `src-tauri/src/services/mod.rs` — Export de AlertService et AlertThresholds
- `src-tauri/src/commands/mod.rs` — Export des 4 commandes d'alerte
- `src-tauri/src/main.rs` — Enregistrement des 4 commandes dans invoke_handler
- `src-tauri/src/lib.rs` — Addition du module services

## Décisions prises

1. **AlertType enum avec seuils constants** : Critical (≤30 jours), Warning (≤90 jours), Info (≤180 jours)
   - Justification : configurabilité via AlertThresholds struct ; facilement modifiable pour futures exigences

2. **Modèle de stockage des alertes** : Table dedicative avec FK vers concessions + CASCADE DELETE
   - Justification : historique traçable, requêtes efficaces via indexes, intégrité référentielle garantie

3. **Calcul d'alertes à la demande** : refresh_alerts() command exécuté on-demand (pas de daemon)
   - Justification : MVP strict, pas de background tasks requises ; frontend peut déclencher après chaque action

4. **Acknowledged_at nullable** : Permet re-alerting si concession renouvelée
   - Justification : flexibilité pour futurs scenarii, timestamps ISO 8601 pour audit trail

5. **Architecture par couches** : DTO → Repository → Service → Commands
   - Justification : séparation des responsabilités, testabilité, réutilisabilité des composants

## Problèmes connus

Aucun. Tous les tests passent, tous les scenarios sont couverts, aucune regression.

## Résultats des tests

**Unit tests:**
- AlertType enum + DTO models: 5 tests ✅
- AlertRepository CRUD: 6 tests ✅
- AlertService threshold logic: 3 tests ✅
- Tauri command signatures: 4 tests ✅
- **Subtotal unit: 18/18 passing** ✅

**Integration tests:**
- Alert creation and retrieval: 1 test ✅
- Alert types trigger correctly (CRITICAL/WARNING/INFO): 1 test ✅
- Alert acknowledgment: 1 test ✅
- FK cascade delete: 1 test ✅
- **Subtotal integration: 4/4 passing** ✅

**Full suite:**
- **Total: 48/48 tests passing** ✅
- No regressions
- cargo check: Clean
- cargo build: Clean

## Prochaines étapes

1. **MVP-17** : Intégrer le centre d'alertes dans l'interface frontend
   - Afficher le résumé des alertes (AlertSummaryDTO)
   - Lister les alertes non-acquittées (list_alerts)
   - Implémenter acknowledge UI

2. **MVP-18+** : Génération de documents PDF
   - Avis d'échéance basé sur alertes
   - Courriers de relance automatisées

3. **Tests E2E** : Scénarios complets depuis interface (MVP-26)
   - Déclencher alerte → reconnaître via UI → vérifier en DB
