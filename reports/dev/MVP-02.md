# MVP-02 — Initialiser le shell Tauri + React + TypeScript

**Date :** 2026-06-15  
**Agent :** frontend  
**Statut :** ✅ Stabilisé  
**Dépend de :** MVP-01 ✅ Terminé

## Objectif

Poser le socle applicatif desktop : shell Tauri + React/TypeScript avec navigation, routage de base, structure frontend documentée et tests initiaux.

## Tâches clés

- [x] Installer dépendances npm (react-router-dom, lucide-react, clsx, tailwind-merge, class-variance-authority)
- [x] Configurer Tailwind CSS v3 (postcss.config.js, tailwind.config.js, src/index.css)
- [x] Mettre à jour tsconfig.json pour JSX (jsx: "react-jsx")
- [x] Créer structure des routes (src/router.tsx avec 8 routes de base)
- [x] Initialiser layout principal (AppLayout avec Sidebar + Header)
- [x] Mettre à jour src/App.tsx pour RouterProvider

## Fichiers créés / modifiés

**Créés :**
- postcss.config.js
- tailwind.config.js
- src/index.css
- src/router.tsx
- src/components/layout/Sidebar.tsx
- src/components/layout/Header.tsx
- src/components/layout/AppLayout.tsx
- src/__tests__/setup.ts

**Modifiés :**
- package.json (dépendances)
- src/main.tsx (import index.css)
- tsconfig.json (jsx: "react-jsx")
- vite.config.ts (test config Vitest)
- src/App.tsx (Router)

## Décisions prises

1. **Tailwind CSS v3** : cohérence avec shadcn/ui, variables CSS pour thème (couleurs sidebar, status).
2. **React Router v6** : routage déclaratif, lazy loading des pages.
3. **Layout unifié** : AppLayout contient Sidebar + Header, avec Outlet pour les pages.
4. **Recherche globale** : intégrée au Header, navigue vers /recherche avec query string.
5. **Icônes** : lucide-react pour tous les icônes (4x4 par défaut).

## Problèmes connus

- Aucun problème fonctionnel identifié.
- Les pages afficheront des stubs jusqu'à MVP-05A (types générés) et MVP-10/11 (données backend).

## Résultats des tests

```bash
$ npx vitest run
 Test Files  3 passed (3)
      Tests  8 passed (8)
```

✅ Compilation TypeScript sans erreur.

## Prochaines étapes

1. MVP-06 : Mettre en place les composants UI de base et le design system.
2. MVP-05A : Générer automatiquement les types TypeScript (specta).
3. MVP-10/11 : Implémenter les commandes Tauri et les services backend.

## Notes pour MVP-06+

Le frontend est prêt à accueillir :
- Composants UI réutilisables (Button, Card, etc.) déjà dans Task 5+ du plan.
- Intégration des types TypeScript générés.
- Implémentation des vues métier (concessions, défunts, etc.).
