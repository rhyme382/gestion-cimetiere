# Audit critique du worktree frontend

Date : 2026-06-16
Agent : orchestrator
Statut : audit uniquement, aucun changement applicatif

## Objet

Vérifier si les nombreuses suppressions frontend visibles dans `git status` sont légitimes, si elles correspondent à des remplacements `.ts` / `.tsx`, et si leur origine relève :

- d'une migration TypeScript ;
- d'un nettoyage d'artefacts ;
- d'une erreur ;
- d'un changement de branche.

## État observé

Le worktree courant contient des suppressions non committées de fichiers `src/**/*.js`, notamment :

- `src/App.js`
- `src/main.js`
- `src/lib/tauri.js`
- `src/components/**.js`
- `src/hooks/**.js`
- `src/types/bindings.js`
- `src/__tests__/**.js`

## Vérification des équivalents TypeScript

### Remplacements confirmés

Les suppressions suivantes ont un équivalent source présent dans le worktree :

- `src/App.js` → `src/App.tsx`
- `src/main.js` → `src/main.tsx`
- `src/lib/tauri.js` → `src/lib/tauri.ts`
- `src/lib/utils.js` → `src/lib/utils.ts`
- `src/components/layout/*.js` → `src/components/layout/*.tsx`
- `src/components/map/CemeteryMap.js` → `src/components/map/CemeteryMap.tsx`
- `src/components/ui/*.js` → `src/components/ui/*.{ts,tsx}`
- `src/hooks/*.js` → `src/hooks/*.ts`
- `src/mocks/cemetery-map.js` → `src/mocks/cemetery-map.ts`
- `src/types/bindings.js` → `src/types/bindings.ts`
- `src/__tests__/setup.js` → `src/__tests__/setup.ts`

### Cas des tests

Les fichiers de tests supprimés ont aussi des équivalents TypeScript présents, même quand l’extension change de `.js` vers `.test.ts` ou `.test.tsx` :

- `src/__tests__/AppLayout.test.js` → `src/__tests__/AppLayout.test.tsx`
- `src/__tests__/CemeteryMap.test.js` → `src/__tests__/CemeteryMap.test.tsx`
- `src/__tests__/Sidebar.test.js` → `src/__tests__/Sidebar.test.tsx`
- `src/__tests__/bindings.test.js` → `src/__tests__/bindings.test.ts`
- `src/__tests__/hooks/useQuery.test.js` → `src/__tests__/hooks/useQuery.test.ts`

## Nature réelle des suppressions

### 1. Migration TypeScript

Oui, en amont.

Le frontend a déjà été migré vers TypeScript : les sources actives sont aujourd’hui en `.ts` et `.tsx`, et le dépôt contient les versions typées correspondantes.

### 2. Nettoyage d’artefacts

Oui, très probablement.

Les fichiers supprimés sont cohérents avec des sorties de transpilation placées dans `src/` :

- leur contenu historique est du JavaScript compilé depuis React/TypeScript ;
- les fichiers `.ts/.tsx` sources existent déjà ;
- un commit précédent `ee78fe2` a explicitement commencé ce nettoyage sur `src/pages/*.js` et `src/router.js` ;
- le script de build a ensuite été corrigé pour éviter la régénération automatique de tels artefacts dans `src/`.

### 3. Erreur

Peu probable.

Aucun des fichiers supprimés inspectés n’apparaît comme une source métier unique ou irremplaçable. Les suppressions portent sur des doublons `.js` d’éléments déjà présents en TypeScript.

### 4. Changement de branche

Cause secondaire possible, mais pas cause racine.

Les suppressions sont aujourd’hui des modifications locales non committées. Un changement de branche peut transporter ces suppressions si elles existaient déjà dans le worktree, mais il n’explique pas leur nature. La cause racine observée est un nettoyage local d’artefacts frontend issus d’une ancienne émission JavaScript.

## Analyse critique

Ces suppressions paraissent légitimes sur le fond :

- elles s’alignent avec une base source TypeScript déjà en place ;
- elles ne retirent pas de logique sans remplaçant ;
- elles prolongent le nettoyage partiel déjà committé autour de MVP-15.

En revanche, elles ne sont pas encore sécurisées par un commit dédié et restent visibles comme suppressions locales massives. Tant qu’elles ne sont ni committées ni explicitement annulées, le worktree reste ambigu et fragile pour les prochains audits.

## Décision

Les suppressions frontend observées correspondent majoritairement à un **nettoyage d’artefacts générés après migration TypeScript**, pas à une perte de code source.

Conclusion obligatoire : **MUST_COMMIT**

## Justification de la conclusion

- `SAFE_TO_IGNORE` serait inadapté, car il s’agit de fichiers **suivis par Git** actuellement supprimés localement.
- `MUST_RESTORE` serait excessif, car les équivalents `.ts/.tsx` existent et la suppression paraît légitime.
- `MUST_COMMIT` est l’option cohérente : ces suppressions doivent être soit validées par un commit de nettoyage global, soit revues explicitement avant d’être abandonnées.

## Recommandation opérationnelle

Avant tout nouveau développement :

1. Regrouper ce nettoyage dans un commit dédié.
2. Vérifier les validations frontend (`tsc`, `vitest`, `build`) sur ce cleanup global.
3. Élargir éventuellement la stratégie d’ignorance/documentation pour éviter la réapparition future d’artefacts `.js` dans `src/`.
