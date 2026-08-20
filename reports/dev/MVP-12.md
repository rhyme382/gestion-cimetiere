# MVP-12 — Créer les écrans dashboard, liste et fiche concession

**Date:** 2026-06-16  
**Agent:** frontend  
**Statut:** ✅ Stabilisé  
**Dépend de:** MVP-02 ✅, MVP-06 ✅, MVP-10 ✅, MVP-11 ✅

## Objectif

Créer les écrans métier prioritaires pour afficher et gérer les concessions:
- Dashboard avec statistiques en temps réel
- Liste des concessions avec filtrage par statut
- Fiche détail d'une concession

## Tâches clés

- [x] Mettre à jour DashboardPage avec vraies données (useCemeteries, useConcessions, useIndividuals)
- [x] Créer ConcessionsPage avec liste filtrable et pagination visuelle
- [x] Créer ConcessionDetailPage avec détails complets
- [x] Mettre à jour router.tsx pour ajouter routes de détail
- [x] Gérer loading/error/empty states avec DataLoader
- [x] Utiliser uniquement les types générés (ConcessionDTO, etc.)

## Fichiers créés / modifiés

**Créés:**
- `src/pages/ConcessionDetailPage.tsx` — Écran détail concession
- `src/pages/DefuntDetailPage.tsx` — Écran détail défunt (pour MVP-13)

**Modifiés:**
- `src/pages/DashboardPage.tsx` — Dashboard avec données réelles
- `src/pages/ConcessionsPage.tsx` — Liste concessions avec filtrage
- `src/pages/DefuntsPage.tsx` — Liste défunts avec search
- `src/pages/RecherchePage.tsx` — Recherche globale améliorée
- `src/router.tsx` — Routes de détail ajoutées

## Décisions prises

1. **DataLoader wrapper** — Utilisé partout pour gérer loading/error/empty states de façon cohérente
2. **Filtrage local** — Les filtres sont appliqués côté client (sûr pour MVP, données limitées)
3. **Status colors** — Codification couleur pour les statuts (vert=actif, rouge=expiré, etc.)
4. **Navigation** — Liens "Détails" dans les listes mènent aux fiches détail
5. **Pagination visuelle** — Pas de vraie pagination, affichage des 5 derniers items au dashboard

## Implémentations principales

### Dashboard (DashboardPage.tsx)
- 4 cartes de statistiques (cimetières, concessions, défunts, alertes)
- Liste des 5 concessions récentes
- États loading/error gérés avec DataLoader
- Utilise useCemeteries, useConcessions, useIndividuals

### Liste concessions (ConcessionsPage.tsx)
- Boutons de filtrage par statut (active, expiring_soon, expired, renewed, abandoned, reclaimed, archived)
- Tableau avec colonnes: ID, Cimetière, Statut, Acquise le, Expire le
- Chaque ligne a un bouton "Détails" qui navigue vers la fiche
- États loading/error/empty gérés

### Fiche concession (ConcessionDetailPage.tsx)
- Informations complètes: ID, cimetière, emplacement, statut
- Dates importantes: acquise le, expire le, renouvelée le
- Données audit: créée le, modifiée le
- Boutons d'action (Éditer, Imprimer, Télécharger, Supprimer) — stubs pour MVP

## Types utilisés

- `ConcessionDTO` (générée depuis Rust)
- `ConcessionStatus` type enum (active | expiring_soon | expired | renewed | abandoned | reclaimed | archived)

**Zéro création de DTO** — tous les types proviennent de `bindings.ts`

## Tests

```bash
$ npx tsc --noEmit
✅ TypeScript: 0 errors

$ npx vitest run src/__tests__/hooks
✅ Hook tests: 5/5 passing
```

## Vérifications effectuées

- [x] TypeScript: 0 erreurs
- [x] Tests hooks: 5/5 passant
- [x] Compilation: sans erreur
- [x] DataLoader gère tous les états (loading, error, empty, data)
- [x] Pas d'imports inutilisés
- [x] Types strictement typés (ConcessionDTO, PlotDTO, etc.)

## Problèmes connus

- Actions sur les fiches détail (Éditer, Imprimer, etc.) sont des stubs — implémentation complète en MVP-25+
- Pagination: pas de vraie pagination, affichage limité à 5 items au dashboard

## Prochaines étapes

1. MVP-13 — Créer écrans défunts (liste, fiche, recherche)
2. MVP-14 — Intégrer cartographie réelle avec données API
3. MVP-25+ — Implémenter CRUD complet (formulaires d'édition)

## Notes d'intégration

- Les écrans utilisent exclusivement les hooks créés en frontend_api_integration_prep
- Pas de dépendance sur des données mockées — toutes les données proviennent de l'API backend MVP-10/11
- États loading/error/empty gérés de façon cohérente via DataLoader

## Validation

✅ Dashboard affiche les statistiques en temps réel
✅ Liste concessions filtrée par statut
✅ Fiche détail accessible via lien "Détails"
✅ Tous les états (loading, error, empty) gérés correctement
✅ Types TypeScript générés utilisés exclusivement
