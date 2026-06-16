# MVP-17 — Intégrer le centre d'alertes minimal dans l'interface

**Date :** 2026-06-16  
**Agent :** frontend  
**Statut :** ✅ Stabilisé  
**Dépend de :** MVP-12 ✅, MVP-13 ✅, MVP-15 ✅, MVP-16 ✅

## Objectif

Intégrer le système d'alertes d'échéance (MVP-16) dans l'interface frontend :
- Afficher le résumé des alertes sur le dashboard
- Créer une page tableau complet des alertes
- Permettre l'acquittement d'alertes
- Afficher les alertes liées à une concession sur sa fiche détail

## Tâches clés

- [x] Ajouter types AlertDTO et AlertSummaryDTO à bindings.ts
- [x] Ajouter appels Tauri pour les alertes (list, summary, refresh, acknowledge)
- [x] Créer hook `useAlerts()` pour récupérer les alertes
- [x] Créer hook `useAlertSummary()` pour résumé du dashboard
- [x] Créer action `acknowledgeAlertAsync()` pour acquitter
- [x] Créer composant `AlertWidget` pour le dashboard
- [x] Créer composant `AlertsTable` pour la page détail
- [x] Mettre à jour AlertesPage pour utiliser AlertsTable
- [x] Ajouter widget d'alertes sur DashboardPage
- [x] Ajouter alertes liées sur ConcessionDetailPage
- [x] Gérer loading/error/empty states
- [x] Vérifier compilation TypeScript
- [x] Tester build production

## Fichiers créés / modifiés

**Créés :**
- ✅ `src/hooks/useAlerts.ts` — Hooks pour alertes (list, summary, acknowledge, refresh)
- ✅ `src/components/alerts/AlertWidget.tsx` — Widget résumé pour dashboard
- ✅ `src/components/alerts/AlertsTable.tsx` — Tableau complet des alertes

**Modifiés :**
- ✅ `src/types/bindings.ts` — Ajouter AlertType, AlertDTO, AlertSummaryDTO
- ✅ `src/lib/tauri.ts` — Ajouter appels Tauri alertes (4 fonctions)
- ✅ `src/hooks/index.ts` — Exporter nouveaux hooks
- ✅ `src/pages/AlertesPage.tsx` — Utiliser AlertsTable au lieu de stub
- ✅ `src/pages/DashboardPage.tsx` — Ajouter AlertWidget
- ✅ `src/pages/ConcessionDetailPage.tsx` — Ajouter alertes liées + acquittement

## Décisions prises

1. **AlertWidget compact** — Affiche résumé avec:
   - Compteur total
   - Couleur selon sévérité (rouge=critique, orange=alerte, bleu=info)
   - Bouton "Voir tous" vers page détail
   - Graceful fallback si aucune alerte

2. **AlertsTable fonctionnelle** — Tableau avec:
   - Sévérité (icône + badge)
   - Lien cliquable vers fiche concession
   - Date d'expiration
   - Urgence en jours (couleur codée)
   - Bouton acquitter par alerte

3. **Alertes sur fiche concession** — Affichage:
   - Section alerte si existe
   - Icône + label selon sévérité
   - Date d'expiration et jours restants
   - Bouton acquitter intégré

4. **Acquittement on-demand** — Pas de polling:
   - Frontend déclenche `acknowledgeAlert(id)`
   - Rafraîchit liste et/ou summary après
   - Pattern simple et réactif

5. **Types générés utilisés** — AlertType enum (CRITICAL|WARNING|INFO):
   - Seuils exposés : CRITICAL (≤30j), WARNING (≤90j), INFO (≤180j)
   - AlertDTO contient tous les champs nécessaires
   - AlertSummaryDTO suffisant pour dashboard

## Implémentations principales

### Hooks (src/hooks/useAlerts.ts)

```typescript
useAlerts(options?) — Hook requête pour list_alerts()
  - Récupère AlertDTO[] (alertes non acquittées)
  - Retourne { data, loading, error, refetch }

useAlertSummary(options?) — Hook requête pour get_alert_summary()
  - Récupère AlertSummaryDTO (compteurs)
  - Retourne { data, loading, error, refetch }

refreshAlertsAsync() — Appel synchrone pour refresh_alerts()
  - Recalcule toutes les alertes
  - Retourne AlertDTO[]

acknowledgeAlertAsync(alert_id) — Appel synchrone pour acknowledge_alert()
  - Acquitte alerte spécifique
  - Retourne boolean
```

### AlertWidget (Dashboard)

Affiche:
- Badge nombre total (rouge si critique, orange si alerte, bleu sinon)
- Compteurs par sévérité (CRITICAL, WARNING, INFO)
- Bouton "Voir tous" → navigation /alertes
- Message "Aucune alerte" si zéro

### AlertsTable (Page Alertes)

Tableau complet avec:
- Sévérité (icône + badge couleur)
- Lien cliquable → fiche concession
- Date d'expiration (format FR)
- Urgence (jours restants, couleur codée)
- Créée le (historique optionnel)
- Bouton acquitter par alerte

### ConcessionDetailPage (Integration)

Affiche section alertes si liées:
- Icône + label sévérité
- Dates + jours restants
- Bouton acquitter inline
- Design cohérent avec card orange

## Types utilisés

```typescript
type AlertType = "CRITICAL" | "WARNING" | "INFO"

interface AlertDTO {
  id: number
  concession_id: number
  alert_type: AlertType
  expected_expiry_date: string (ISO 8601)
  days_until_expiry: number
  created_at: string (ISO 8601)
  acknowledged_at: string | null
}

interface AlertSummaryDTO {
  total_alerts: number
  critical_count: number
  warning_count: number
  info_count: number
}
```

**Zéro création de DTO** — Types proviennent de MVP-16 backend

## Tests

```bash
$ npx tsc --noEmit
✅ TypeScript: 0 errors

$ npx vitest run src/__tests__/hooks
✅ Hook tests: 5/5 passing

$ npm run build
✅ Build successful (276.40 kB, 89.50 kB gzip)
```

## Vérifications effectuées

- [x] TypeScript: 0 erreurs
- [x] Tests hooks: 5/5 passant
- [x] Compilation: sans erreur
- [x] Build npm: ✓ complète (276.40 kB bundle)
- [x] Pas d'imports inutilisés
- [x] Types strictement typés (AlertType enum)
- [x] DataLoader gère tous les états
- [x] Acquittement réactif et immédiat

## Problèmes connus

**Aucun problème fonctionnel identifié.**

**Limitations acceptées (futures MVP) :**
- Pas de pagination vraie pour list_alerts (acceptable si < 500 alertes MVP)
- Pas de polling automatique (frontend décide timing)
- Pas de real-time/SSE (on-demand sufficient pour MVP)
- Pas de filtrage avancé (sévérité, date, concession)

## Architecture

```
DashboardPage
  ├── AlertWidget (get_alert_summary)
  │   └── Badge compteurs
  │   └── Bouton "Voir tous"
  └── [Stats cards, Recent concessions]

AlertesPage
  └── AlertsTable (list_alerts)
      └── Tableau complet avec actions

ConcessionDetailPage
  ├── [Localisation]
  ├── [Alertes liées] (filtered from list_alerts)
  │   └── Badge + acquitter
  └── [Détails concession]
```

## Intégrations avec MVP-16 (Backend)

**Commandes Tauri exploitées :**
1. `list_alerts()` → Vec<AlertDTO> — AlertsTable + filtering
2. `get_alert_summary()` → AlertSummaryDTO — AlertWidget dashboard
3. `refresh_alerts()` → Vec<AlertDTO> — optionnel (post-action)
4. `acknowledge_alert(id)` → bool — boutons acquitter

**Pas de modification backend requise** — Utilise API MVP-16 existante

## Prochaines étapes

1. **MVP-18** — Génération PDF :
   - Avis d'échéance basé sur AlertDTO
   - Courriers de relance automatisés

2. **MVP-19** — Écran export PDF simple

3. **Post-MVP** — Améliorations alertes :
   - Pagination pour list_alerts()
   - Filtres avancés (sévérité, date, concession)
   - Polling/SSE pour real-time
   - Webhook notifications

## Validation

✅ Hook `useAlerts()` récupère list_alerts() correctement  
✅ Hook `useAlertSummary()` récupère get_alert_summary() correctement  
✅ Action `acknowledgeAlertAsync()` utilise acknowledge_alert()  
✅ AlertWidget affiche résumé et badge compteurs  
✅ AlertsTable affiche liste complète avec contexte  
✅ Alertes liées visible sur fiche concession  
✅ Acquittement immédiat et réactif  
✅ Tous les états (loading, error, empty) gérés  
✅ Types AlertType enum utilisés correctement  
✅ Build production réussie  
✅ Tests unitaires passants  

## Conclusion

**MVP-17 stabilise l'intégration des alertes** en fournissant :
✅ Hooks réutilisables pour tous les cas d'usage  
✅ Widget compact pour dashboard  
✅ Tableau complet pour page détail  
✅ Acquittement intégré sur fiches  
✅ États d'erreur et chargement gérés  
✅ Architecture propre et maintenable  
✅ Prêt pour intégration backend réelle (MVP-16 ✅)  

**Blocages résolus :** Alertes d'échéance pleinement intégrées et visibles, acquittement fonctionnel.

**Prochains jalons :** MVP-18 (documents PDF), MVP-19 (export simple), puis améliorations alertes optionnelles.
