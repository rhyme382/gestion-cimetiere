# Correction — FP001-T03

## Problème détecté

Le verdict Codex a identifié que le critère d'acceptation n'était pas entièrement satisfait :

**Critère** : `src/lib/tauri.ts` et les hooks dédiés invoquent les commandes avec les bons noms d'arguments et restent testés côté Vitest.

**Problème** : Le hook `src/hooks/useMunicipalities.ts` et ses helpers async n'étaient pas couverts par des tests Vitest.

## Correction apportée

### Fichier créé

- `src/__tests__/hooks/useMunicipalities.test.ts` : Suite de tests complète pour tous les hooks de commune (16 tests)

### Couverture des tests

#### useMunicipalities() — 6 tests
- Récupère et retourne la liste des communes
- Gère une liste vide
- Gère les erreurs de récupération
- Respecte l'option `enabled`
- Implémente la refetch

#### useMunicipality(id) — 4 tests
- Récupère une commune unique quand id est fourni
- N'effectue pas la récupération quand id est null
- Respecte l'option `enabled`
- Gère les erreurs de récupération

#### createMunicipalityAsync() — 3 tests
- Crée une commune avec succès
- Propage les erreurs comme objets Error
- Convertit les exceptions non-Error en Error

#### updateMunicipalityAsync() — 2 tests
- Met à jour une commune avec succès
- Propage les erreurs comme objets Error

#### deleteMunicipalityAsync() — 2 tests
- Supprime une commune avec succès
- Propage les erreurs comme objets Error

## Résultats des tests

```
npm run test — 155 tests passed, 11 test files passed
npm run test -- src/__tests__/bindings.test.ts src/__tests__/tauri.test.ts — 50 tests passed
npm run test -- src/__tests__/hooks/useMunicipalities.test.ts — 16 tests passed
```

## Critères de validation

✅ `src/types/bindings.ts` reflète les DTO/requêtes de commune et les nouveaux champs des cimetières
✅ `src/lib/tauri.ts` et les hooks dédiés invoquent les commandes avec les bons noms d'arguments
✅ Les hooks restent testés côté Vitest (nouveaux tests ajoutés)
✅ Les tests TypeScript verrouillent la stabilité du contrat sérialisé

## État de la tâche

La tâche FP001-T03 est maintenant complète et tous les critères d'acceptation sont satisfaits.
