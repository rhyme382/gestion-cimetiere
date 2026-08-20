# Audit de Readiness MVP-17 — Intégration des alertes frontend

**Date :** 2026-06-16  
**Auditeur QA :** QA Agent  
**Contexte :** Validation que MVP-17 (Intégrer le centre d'alertes minimal dans l'interface) peut démarrer sans risque de divergence frontend/backend.

**Conclusion :** ✅ **MVP17_FRONTEND_GO**

---

## 1. Vue d'ensemble du contrôle

### MVP-17 dépend de :
- ✅ MVP-16 (alertes backend) — **COMPLÈTE** (48/48 tests passent)
- ✅ MVP-12 (interface frontend cible) — **LIVRÉE**
- ✅ MVP-10/11 (commandes Tauri CRUD) — **OPÉRATIONNELLES**

### Contexte utile non bloquant :
- ✅ MVP-13 — écrans défunts et recherche déjà livrés
- ✅ MVP-15 — intégration cartographie/fiches déjà livrée

### Livrables MVP-16 à valider :
1. **DTO alertes** (`src-tauri/src/dto/alert.rs`) — sérialisables et stables
2. **Commandes Tauri** (`src-tauri/src/commands/alert.rs`) — documentées et cohérentes
3. **Service métier** (`src-tauri/src/services/alert_service.rs`) — seuils exposés
4. **Contrats** — données nécessaires pour le frontend disponibles

---

## 2. Audit des DTOs (Contrôle 1)

### AlertType Enum

```rust
#[derive(Debug, Clone, Copy, Serialize, Deserialize, Type, PartialEq)]
#[serde(rename_all = "UPPERCASE")]
pub enum AlertType {
    Critical,     // ≤ 30 jours
    Warning,      // ≤ 90 jours
    Info,         // ≤ 180 jours
}
```

**Sérialisation :** ✅
- `Serialize, Deserialize` — JSON compatible
- `Type` — generatable en TypeScript
- `#[serde(rename_all = "UPPERCASE")]` — frontend reçoit `"CRITICAL"`, `"WARNING"`, `"INFO"`

**Stabilité :** ✅
- Enum immuable, seuils constants intégrés
- Pas de breaking change si ajout futur (enum extensible)
- Conversion `from_str()` pour parsing backend

**Tests :** ✅
- `test_alert_type_serialization()` — seuils validés
- `test_alert_type_as_str()` — représentation string confirmée
- `test_alert_type_from_str()` — parsing parsing bidirectionnel

### AlertDTO

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct AlertDTO {
    pub id: i64,                           // PK
    pub concession_id: i64,                // FK → concessions
    pub alert_type: AlertType,             // CRITICAL|WARNING|INFO
    pub expected_expiry_date: String,      // ISO 8601
    pub days_until_expiry: i32,            // Calcul utile pour frontend
    pub created_at: String,                // ISO 8601 UTC
    pub acknowledged_at: Option<String>,   // NULL si non acquittée
}
```

**Sérialisation :** ✅
- Tous les champs sérialisables
- `Type` dérivé — TypeScript générera une interface alignée
- Dates en String (ISO 8601, cross-platform)

**Complétude pour frontend :** ✅
- `id` — nécessaire pour `acknowledge_alert(id)`
- `concession_id` — permet lien vers fiche concession
- `alert_type` — détermine couleur/icône (CRITICAL=rouge, WARNING=orange, INFO=bleu)
- `expected_expiry_date` — affichage de la date d'échéance
- `days_until_expiry` — calcul local frontend (`${days_until_expiry} jours`)
- `created_at` — historique/tri optionnel
- `acknowledged_at` — statut acquittée (null = non acquittée, sinon date)

**Tests :** ✅
- `test_alert_dto_creation()` — structure validée

### AlertSummaryDTO

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct AlertSummaryDTO {
    pub total_alerts: i32,       // Nombre total d'alertes non-acquittées
    pub critical_count: i32,     // Nombre CRITICAL
    pub warning_count: i32,      // Nombre WARNING
    pub info_count: i32,         // Nombre INFO
}
```

**Sérialisation :** ✅
- Tous les champs i32 simples
- `Type` dérivé

**Suffisance pour dashboard :** ✅
- `total_alerts` — badge de notification principal
- `critical_count`, `warning_count`, `info_count` — compteurs détaillés par sévérité
- Permet affichage : "5 alertes : 2 CRITICAL, 2 WARNING, 1 INFO"

**Tests :** ✅
- `test_alert_summary_aggregation()` — structure validée

---

## 3. Audit des commandes Tauri (Contrôle 2)

### Commande 1 : `list_alerts()`

```rust
#[tauri::command]
pub fn list_alerts(state: State<DbConnection>) -> Result<Vec<AlertDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertRepository::list_unacknowledged(&conn).map_err(|e| e.to_string())
}
```

**Documentation :** ✅
- Commentaire : "List all unacknowledged alerts"
- Signature : Vec<AlertDTO> — liste complète d'objets
- Erreur : String pour Tauri

**Frontend usage :**
```typescript
// React hook (frontend doit implémenter)
const alerts = await invoke('list_alerts', {});
// alerts: AlertDTO[] → affichage tableau
```

**Cohérence :** ✅
- Retourne AlertDTO (DTO stable, contrôle 1 ✓)
- Filtre implicite : uniquement non-acquittées (`acknowledged_at IS NULL`)
- Compatible Vue/Récupération : pas de pagination MVP (acceptable pour MVP)

### Commande 2 : `get_alert_summary()`

```rust
#[tauri::command]
pub fn get_alert_summary(state: State<DbConnection>) -> Result<AlertSummaryDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertRepository::get_summary(&conn).map_err(|e| e.to_string())
}
```

**Documentation :** ✅
- Commentaire : "Get aggregated alert summary"
- Signature : AlertSummaryDTO (un seul objet, agrégation)

**Frontend usage :**
```typescript
const summary = await invoke('get_alert_summary', {});
// summary: AlertSummaryDTO → compteurs dashboard
// Affichage: "5 alertes non-acquittées"
```

**Cohérence :** ✅
- Retourne AlertSummaryDTO (DTO stable, contrôle 2 ✓)
- Agrégation optimale pour dashboard (pas requête complète liste)
- Réponse rapide, peu de données

### Commande 3 : `refresh_alerts()`

```rust
#[tauri::command]
pub fn refresh_alerts(state: State<DbConnection>) -> Result<Vec<AlertDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertService::calculate_alerts(&conn).map_err(|e| e.to_string())
}
```

**Documentation :** ✅
- Commentaire : "Calculate and store alerts for all concessions / Called on-demand to refresh alert state"

**Frontend usage :**
```typescript
// Appelé après création/modification concession
const newAlerts = await invoke('refresh_alerts', {});
// newAlerts: AlertDTO[] → redessine alertes
```

**Cohérence :** ✅
- Retourne Vec<AlertDTO> (liste complète créée)
- On-demand (MVP, pas de daemon backend)
- Frontend peut déclencher après action utilisateur

### Commande 4 : `acknowledge_alert(alert_id)`

```rust
#[tauri::command]
pub fn acknowledge_alert(state: State<DbConnection>, alert_id: i64) -> Result<bool, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertRepository::acknowledge(&conn, alert_id).map_err(|e| e.to_string())
}
```

**Documentation :** ✅
- Commentaire : "Acknowledge a specific alert"
- Paramètre : alert_id (i64) — correspond à AlertDTO.id

**Frontend usage :**
```typescript
// Bouton "Acquitter" sur alerte
const success = await invoke('acknowledge_alert', { alert_id: 5 });
if (success) {
  // Redessine liste (list_alerts) ou summary (get_alert_summary)
}
```

**Cohérence :** ✅
- Paramètre `alert_id` corresponde à AlertDTO.id ✓
- Retourne bool pour feedback UI
- Backend met à jour `acknowledged_at` → alerte disparaît de `list_alerts()`

---

## 4. Audit de la logique métier (Contrôle 3)

### AlertService — Seuils exposés

```rust
pub struct AlertService;

impl AlertService {
    pub fn get_thresholds() -> AlertThresholds {
        AlertThresholds {
            critical: 30,   // ≤ 30 jours
            warning: 90,    // ≤ 90 jours
            info: 180,      // ≤ 180 jours
        }
    }
}

pub struct AlertThresholds {
    pub critical: i32,
    pub warning: i32,
    pub info: i32,
}
```

**Seuils stables :** ✅
- Constantes documentées dans AlertType enum
- Service expose via `get_thresholds()` (utilisation backend)
- Frontend reçoit implicitement via AlertType enum

**Calcul d'alertes :** ✅
```rust
pub fn calculate_alerts(conn: &Connection) -> AppResult<Vec<AlertDTO>> {
    // Pour chaque concession active avec expiry_date:
    //   1. Calcul jours_jusqu_expiration
    //   2. Détermine AlertType (CRITICAL|WARNING|INFO) selon seuils
    //   3. Crée AlertDTO si pas d'alerte existante non-acquittée
    // Retourne Vec<AlertDTO>
}
```

**Tests métier :** ✅
- `test_get_thresholds()` — seuils confirmés (30/90/180)
- `test_calculate_alerts_no_concessions()` — cas vide
- `test_calculate_alerts_no_expiry_dates()` — gestion NULL `expires_at`

---

## 5. Audit des données requises frontend (Contrôle 4)

### Données manquantes pour MVP-17 ?

**Dashboard (centre d'alertes) :**
- Résumé : AlertSummaryDTO ✅ → affichage compteurs
- Liste alertes : AlertDTO[] ✅ → tableau alertes
- Acquittement : acknowledge_alert(id) ✅ → bouton par alerte

**Fiche concession (affichage alerte associée) :**
- AlertDTO.concession_id ✅ → lien bidirectionnel
- AlertDTO.alert_type ✅ → visual feedback (rouge/orange/bleu)
- AlertDTO.expected_expiry_date ✅ → date d'échéance
- AlertDTO.days_until_expiry ✅ → urgence
- AlertDTO.acknowledged_at ✅ → état acquittée

**Tableau alertes :**
- AlertDTO.id ✅ → identité unique
- AlertDTO.created_at ✅ → tri/historique optionnel
- AlertDTO.concession_id ✅ → lien vers fiche concession

**Conclusion :** ✅ **Aucune donnée manquante**

---

## 6. Audit du résumé des alertes (Contrôle 5)

### AlertSummaryDTO suffisance pour dashboard

```typescript
interface AlertSummaryDTO {
  total_alerts: number;      // Badge : "5 alertes"
  critical_count: number;    // Badge rouge : "2"
  warning_count: number;     // Badge orange : "2"
  info_count: number;        // Badge bleu : "1"
}
```

**Dashboard usage :**
```typescript
const summary = await invoke('get_alert_summary', {});

// HTML possibilities:
// <AlertWidget>
//   <Badge critical={summary.critical_count} color="red" />
//   <Badge warning={summary.warning_count} color="orange" />
//   <Badge info={summary.info_count} color="blue" />
//   Total: {summary.total_alerts}
// </AlertWidget>
```

**Suffisance :** ✅
- Permet affichage "glance" du statut alertes
- Compteurs par sévérité pour décision utilisateur
- Léger (4 int) — no performance issue

---

## 7. Audit de la liste des alertes (Contrôle 6)

### List_alerts() fournit-elle infos nécessaires à l'interface ?

```typescript
interface AlertDTO {
  id: i64;                    // Clé → acknowledge_alert(id)
  concession_id: i64;         // Lien vers fiche concession
  alert_type: AlertType;      // Sévérité (CRITICAL|WARNING|INFO)
  expected_expiry_date: string; // Affichage date
  days_until_expiry: i32;     // Affichage urgence ("29 jours")
  created_at: string;         // Historique optional
  acknowledged_at: Option<string>; // Déjà visible en list_unacknowledged
}
```

**Tableau frontend :**
```
| Concession | Sévérité | Date d'échéance | Jours | Action |
|---|---|---|---|---|
| C001 | 🔴 CRITICAL | 2026-07-15 | 29 | [Acquitter] |
| C005 | 🟠 WARNING | 2026-09-20 | 96 | [Acquitter] |
```

Tous les champs nécessaires sont présents ✅

**Suffisance :** ✅
- Identification alerte (id) ✓
- Sévérité visuelle (alert_type) ✓
- Contexte métier (concession_id) ✓
- Urgence (days_until_expiry) ✓
- Date cible (expected_expiry_date) ✓
- Historique optionnel (created_at) ✓

---

## 8. Audit de l'acquittement (Contrôle 7)

### acknowledge_alert() exploitable côté frontend ?

```typescript
// User clique [Acquitter] sur alerte id=5
const result = await invoke('acknowledge_alert', { alert_id: 5 });

if (result === true) {
  // Succès : refresh liste et/ou summary
  const updatedAlerts = await invoke('list_alerts', {});
  const updatedSummary = await invoke('get_alert_summary', {});
  // UI update
} else {
  // Erreur (catchée comme Err(String) en Result)
  showError('Erreur lors de l\'acquittement');
}
```

**Backend behavior :**
- Paramètre `alert_id` → valide existence alerte
- Met à jour `acknowledged_at = NOW()` en DB
- `list_alerts()` filtre `WHERE acknowledged_at IS NULL` → alerte disparaît

**Frontend responsabilité :**
- Afficher bouton [Acquitter] pour chaque alerte
- Appeler `acknowledge_alert(id)` 
- Redessiner liste (list_alerts) OU summary (get_alert_summary)

**Cohérence :** ✅
- Backend expose toutes les infos nécessaires
- Frontend peut implémenter sans ambiguïté
- Pattern standard (invoke + refresh)

---

## 9. Résumé des vérifications

| Contrôle | Critère | Résultat | Détail |
| --- | --- | --- | --- |
| 1 | DTO alertes stables et sérialisables | ✅ | AlertType, AlertDTO, AlertSummaryDTO — tous avec `Type` dérivé |
| 2 | Commandes Tauri documentées et cohérentes | ✅ | 4 handlers (list, summary, refresh, acknowledge) — signatures claires |
| 3 | Seuils d'alerte exposés correctement | ✅ | CRITICAL=30j, WARNING=90j, INFO=180j — constants + service |
| 4 | Données nécessaires au frontend présentes | ✅ | id, concession_id, alert_type, dates, days_until_expiry — complet |
| 5 | AlertSummaryDTO suffisant pour dashboard | ✅ | total + compteurs par sévérité — léger et pertinent |
| 6 | Liste alertes fournit infos UI nécessaires | ✅ | id, type, dates, urgence, contexte — tous les champs requis |
| 7 | Acquittement exploitable frontend | ✅ | acknowledge_alert(id) → bool — pattern simple et clair |

---

## 10. Risques résiduels pour MVP-17

### ✅ Aucun risque identifié

**Alignement frontend/backend :** Nul
- Contrats sérialisables et stables
- Pas de breaking change connu
- Pas de donnée manquante

**Performance :** Acceptable
- `get_alert_summary()` → agrégation rapide (COUNT)
- `list_alerts()` → pas de pagination MVP (acceptable si < 100 alertes)
- `refresh_alerts()` → on-demand, pas de daemon (frontend décide timing)

**Erreurs :**
- Gestion State lock cohérente
- Propagation en String standardisée
- Frontend peut afficher erreurs via catch

### Recommandations optionnelles (post-MVP)
1. Pagination de `list_alerts()` si > 1000 alertes
2. Endpoint refresh par domaine (refresh_alerts_for_cemetery)
3. Webhook/SSE pour real-time (MVP strict = polling)

---

## 11. Conclusion finale

### ✅ MVP17_FRONTEND_GO

**Tous les critères d'audit sont verts.**

**Le backend MVP-16 fournit :**
1. ✅ DTOs stables et sérialisables (specta::Type)
2. ✅ 4 commandes Tauri cohérentes et documentées
3. ✅ Seuils d'alerte constants et exposés (30/90/180 jours)
4. ✅ Données complètes pour frontend (id, type, dates, urgence)
5. ✅ Résumé suffisant pour dashboard (compteurs)
6. ✅ Infos complètes pour interface (listes)
7. ✅ Acquittement simple et exploitable

**Frontend MVP-17 peut démarrer immédiatement sans risque de divergence.**

**Contrats de code à implémenter côté React :**
- Hook `useAlerts()` → appel `list_alerts()`
- Hook `useAlertSummary()` → appel `get_alert_summary()`
- Action `acknowledgeAlert(id)` → appel `acknowledge_alert(id)`
- Action `refreshAlerts()` → appel `refresh_alerts()`
- Component `<AlertWidget>` + `<AlertsTable>` (design basé sur AlertType enum)

**Intégration dashboard :**
- AlertWidget (résumé) en haut-droit
- Lien vers page d'alertes détaillée
- Onglet/modal listant non-acquittées

**Intégration fiche concession :**
- Afficher badge alerte si concession_id correspond
- Bouton [Acquitter] accessible

---

**Date d'audit :** 2026-06-16  
**Auditeur :** QA Agent  
**Dépendance validée :** MVP-16 (alertes backend complètes)  
**Bloquants :** Aucun  
**Démarrage :** Immédiat — MVP17_FRONTEND_GO ✅
