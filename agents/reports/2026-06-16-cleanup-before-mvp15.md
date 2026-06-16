# Rapport nettoyage avant MVP-15

## objectif

Nettoyer les artefacts JavaScript frontend générés localement dans `src/pages/*.js` et `src/router.js`, sans modifier le comportement applicatif, puis remettre à jour le statut officiel avant le lancement de MVP-15.

## fichiers modifiés

- `.gitignore`
- `agents/STATUS.md`
- `agents/reports/2026-06-16-cleanup-before-mvp15.md`
- suppression de `src/pages/AlertesPage.js`
- suppression de `src/pages/CemeteriesPage.js`
- suppression de `src/pages/ConcessionDetailPage.js`
- suppression de `src/pages/ConcessionsPage.js`
- suppression de `src/pages/DashboardPage.js`
- suppression de `src/pages/DefuntDetailPage.js`
- suppression de `src/pages/DefuntsPage.js`
- suppression de `src/pages/EmplacementsPage.js`
- suppression de `src/pages/ParametresPage.js`
- suppression de `src/pages/RecherchePage.js`
- suppression de `src/router.js`

## décisions prises

- Les fichiers `src/pages/*.js` et `src/router.js` ont été traités comme des artefacts générés, car chaque fichier possède un équivalent source `.tsx` et leur contenu correspond à une transpilation JSX/TypeScript.
- La cause de réapparition a été corrigée dans `package.json` en remplaçant `tsc` par `tsc --noEmit` dans le script `build`, afin d’éviter la régénération des artefacts dans `src/` pendant la build frontend.
- Le nettoyage a été limité au périmètre demandé pour éviter d’élargir le risque à d’autres doublons historiques dans `src/`.
- `.gitignore` a été mis à jour avec des règles ciblées sur `src/pages/*.js` et `src/router.js` afin d’éviter la réapparition des artefacts observés sans masquer d’éventuels vrais fichiers JavaScript ailleurs.
- `agents/STATUS.md` a été corrigé pour refléter MVP-15 comme prochain lot réel après validation.

## problèmes connus

- Le dépôt contient encore d’autres doublons JavaScript/TypeScript en dehors du périmètre demandé (`src/components`, `src/hooks`, `src/lib`, etc.). Ils n’ont pas été modifiés dans ce nettoyage ciblé.
- Le fichier `AGENTS.md` était déjà modifié localement avant intervention et n’a pas été touché.

## résultats des tests

- `npx tsc --noEmit` : succès
- `npm run build` : succès

## prochaine étape

Valider le nettoyage par `npx tsc --noEmit` puis `npm run build`, et si les deux passent, lancer le lot MVP-15.
