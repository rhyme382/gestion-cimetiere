# MVP-06 — Mettre en place la base de composants UI et le shell de navigation

**Date :** 2026-06-15  
**Agent :** frontend  
**Statut :** ✅ Stabilisé (préparation pour MVP-12+)  
**Dépend de :** MVP-02 ✅, MVP-05A ✅

## Objectif

Créer un design system minimal, les composants UI réutilisables (Button, Badge, Card, Input, Label, Separator) et les 8 pages stubs de navigation. Les types TypeScript sont en miroir exact des DTOs Rust.

## Tâches clés

- [x] Créer composants UI de base (Button, Badge, Card, Input, Label, Separator)
- [x] Créer wrapper Tauri typé (src/lib/tauri.ts) avec 18 commandes
- [x] Créer types TypeScript (src/types/bindings.ts) mirroir exact des DTOs Rust
- [x] Créer 8 pages stubs (Dashboard, Cimeteries, Concessions, Defunts, Emplacements, Recherche, Alertes, Parametres)
- [x] Créer tests unitaires (AppLayout, Sidebar, types bindings)
- [x] Vérifier compilation TypeScript et tests

## Fichiers créés / modifiés

**Créés :**
- src/types/bindings.ts (5 DTOs + 8 requêtes, mirroir exact Rust)
- src/lib/utils.ts (cn() helper, formatDate)
- src/lib/tauri.ts (18 commandes typées)
- src/components/ui/button.tsx (6 variantes, 4 sizes)
- src/components/ui/badge.tsx (8 variantes)
- src/components/ui/card.tsx (5 fonctions: Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter)
- src/components/ui/input.tsx
- src/components/ui/label.tsx
- src/components/ui/separator.tsx
- src/pages/DashboardPage.tsx
- src/pages/CemeteriesPage.tsx
- src/pages/ConcessionsPage.tsx
- src/pages/DefuntsPage.tsx
- src/pages/EmplacementsPage.tsx
- src/pages/RecherchePage.tsx
- src/pages/AlertesPage.tsx
- src/pages/ParametresPage.tsx
- src/__tests__/AppLayout.test.tsx
- src/__tests__/Sidebar.test.tsx
- src/__tests__/bindings.test.ts

## Décisions prises

1. **Types TypeScript manuels** : en attendant specta/tauri-specta (post-MVP-06). Commentaire explicite dans bindings.ts.
2. **Composants UI simples** : class-variance-authority pour variants, cn() pour merge Tailwind.
3. **Design tokens** : variables CSS pour cohérence (sidebar: bleu sombre 222 47% 16%, primary: bleu ciel).
4. **Pages stubs** : affichent des messages clairs sur dépendances (MVP-10/11 pour données).
5. **Recherche** : intégrée à Header (MVP-02), page dédiée avec query params.

## Problèmes connus

- specta/tauri-specta en RC : génération TypeScript manuelle actuellement, sera automatisée en MVP-06 extension.
- Pages métier profond (listes avec données, formulaires CRUD) reportées à MVP-12+.

## Résultats des tests

```bash
$ npx vitest run
 Test Files  3 passed (3)
      Tests  8 passed (8)
   Start at  18:12:29
   Duration  964ms
```

✅ TypeScript sans erreur : `npx tsc --noEmit` ✓

## Vérifications effectuées

- [x] Compilation TypeScript : 0 erreur
- [x] Tests Vitest : 8/8 passing
- [x] Types bindings : cohérence Rust/TypeScript vérifiée
- [x] Composants UI : tous rendus sans erreur de props
- [x] Routage : 8 routes déclarées + lazy loading

## Prochaines étapes

1. MVP-05A extension : intégrer generation specta pour auto-sync Rust ↔ TypeScript.
2. MVP-12 : Implémenter Dashboard avec statistiques (cimeteries, concessions, defunts, alertes).
3. MVP-13 : Implémenter listes + fiches (concessions, defunts) avec pagination et filtres.
4. MVP-14 : Intégrer cartographie simple avec sélection d'emplacements.

## Notes d'architecture

- **Isolation du contrat Tauri** : src/lib/tauri.ts centralise tous les appels invoke(), facilite mock et test.
- **Types génériques** : CemeteryDTO, PlotDTO, etc. peuvent être étendues sans impacter le reste du frontend.
- **Layout réutilisable** : AppLayout sert de base pour tous les écrans via Outlet du router.
- **Composants composables** : Card (Card + CardHeader + CardTitle + CardContent) suit pattern shadcn.

## Commits

Tous les fichiers sont prêts pour un commit atomique "feat(frontend): MVP-02+MVP-06 shell Tauri/React, design system, navigation, types Rust".

## Validation pour MVP-12+

Le frontend est prêt pour implémenter les écrans métier :
- Types TypeScript stables.
- Routage en place.
- Composants UI testés.
- Tests initiaux validés.
