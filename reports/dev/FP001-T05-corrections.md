# Rapport de Correction — FP001-T05

## Statut
✅ Corrections appliquées et testées avec succès

## Résumé
Les deux problèmes majeurs identifiés par la revue Codex ont été corrigés :
1. L'état d'erreur de `/cimetieres` est maintenant récupérable
2. Les créations et modifications rafraîchissent l'affichage immédiatement

## Problèmes corrigés

### 1. Erreur non récupérable (R5-AC2)

**Problème** : Le composant `DataLoader` supporte un callback `onRetry`, mais `CemeteriesPage` ne le transmettait pas, empêchant l'utilisateur de réessayer après une erreur de chargement.

**Correction** :
```typescript
// src/pages/CemeteriesPage.tsx, ligne 217
<DataLoader
  loading={loading}
  error={error}
  data={displayData}
  onRetry={refetch}  // ← Ajout du callback de reprise
  emptyState={{...}}
>
```

**Résultat** : L'utilisateur peut maintenant cliquer sur le bouton "Réessayer" pour relancer le chargement après une erreur.

### 2. Rafraîchissement retardé (R5-AC3, R5-AC4)

**Problème** : Le `refetch()` était différé de 1500 ms après la création/modification réussie, causant une mise à jour retardée de l'affichage.

**Correction** :
```typescript
// src/pages/CemeteriesPage.tsx, lignes 74-78
refetch();  // Appel immédiat sans délai

setTimeout(() => {
  setShowSuccess(false);  // Seul ce délai est conservé
}, 1500);
```

**Résultat** : Les nouvelles lignes créées et les valeurs modifiées s'affichent immédiatement dans la liste.

## Tests modifiés

### Ajouts
- **Test de reprise d'erreur** : Vérifie que le bouton "Réessayer" fonctionne après une erreur de chargement

### Améliorations
- **Test de création** : Configuration robuste du mock avec `mockImplementation()` et compteur d'appels
- **Test de modification** : Même approche pour garantir plusieurs appels à `listCemeteries()`

## Résultats des tests

```
✅ Test Files  3 passed (3)
✅ Tests  52 passed (52)
```

Toutes les suites de test passent :
- `src/__tests__/cemeteries-page.test.tsx` ✅
- `src/__tests__/cemetery-form.test.tsx` ✅
- `src/__tests__/tauri.test.ts` ✅

## Fichiers modifiés

| Fichier | Changements |
|---------|-----------|
| `src/pages/CemeteriesPage.tsx` | 2 modifications : ajout de `onRetry={refetch}` et rafraîchissement immédiat |
| `src/__tests__/cemeteries-page.test.tsx` | Ajout test reprise d'erreur, amélioration tests création/modification |

## Critères d'acceptation validés

- ✅ **R5-AC2** : L'écran Cimetières affiche une erreur récupérable avec bouton "Réessayer"
- ✅ **R5-AC3** : Création de cimetière avec mise à jour immédiate de la liste
- ✅ **R5-AC4** : Modification de cimetière avec mise à jour immédiate sans rechargement externe

## Prochaines étapes

Les modifications sont prêtes pour intégration. Tous les tests passent et les critères d'acceptation sont validés.
