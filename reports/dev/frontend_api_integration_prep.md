# Frontend API Integration Preparation

**Date:** 2026-06-15  
**Agent:** frontend  
**Status:** ✅ Stabilisé (couche d'intégration prête)  
**Dépend de:** MVP-02 ✅, MVP-06 ✅, MVP-05A ✅

## Objectif

Préparer la couche frontend d'intégration des commandes Tauri sans créer les écrans métier complets (MVP-12/13). Fournir les hooks, services et composants d'état pour faciliter l'implémentation future.

## Tâches clés

- [x] Créer hook générique `useQuery` pour les requêtes Tauri
- [x] Créer hooks spécifiques pour chaque entité (useCemeteries, usePlots, useConcessions, useIndividuals)
- [x] Créer fonctions async pour les mutations (create*, update*, delete*)
- [x] Créer composants d'état (LoadingSpinner, ErrorMessage, EmptyState, DataLoader)
- [x] Créer types d'interface pour les hooks
- [x] Créer tests unitaires pour useQuery
- [x] Créer exports centralisés (index files)

## Fichiers créés

### Hooks (src/hooks/)

**useQuery.ts**
- Hook générique pour les requêtes asynchrones
- Gère loading, error, data states
- Supporte enabled flag, callbacks onSuccess/onError
- Fonction refetch() pour rechargement manuel

**useCemeteries.ts**
- `useCemeteries()` — liste tous les cimetières
- `useCemetery(id)` — récupère un cimetière spécifique
- `createCemeteryAsync()`, `updateCemeteryAsync()`, `deleteCemeteryAsync()`

**usePlots.ts**
- `usePlots(cemeteryId)` — liste les emplacements d'un cimetière
- `usePlot(id)` — récupère un emplacement spécifique
- `createPlotAsync()`, `updatePlotAsync()`

**useConcessions.ts**
- `useConcessions()` — liste toutes les concessions (optionnel: filtre par cimetière)
- `useConcession(id)` — récupère une concession spécifique
- `createConcessionAsync()`, `updateConcessionAsync()`

**useIndividuals.ts**
- `useIndividuals()` — liste tous les individus (défunts, concessionnaires, etc.)
- `useIndividual(id)` — récupère un individu spécifique
- `useSearchIndividuals(query)` — recherche par query string
- `createIndividualAsync()`, `updateIndividualAsync()`

**useBurials.ts**
- `createBurialAsync()` — crée un enregistrement d'inhumation

**index.ts** — Export centralisé de tous les hooks

### Composants UI (src/components/ui/)

**loading-spinner.tsx**
- Spinner animé avec 3 tailles (sm, md, lg)
- Classe CSS personnalisable

**error-message.tsx**
- Affiche les erreurs avec icône AlertCircle
- Bouton "Réessayer" optionnel
- Style destructive/error

**empty-state.tsx**
- Affiche un état vide avec icône et titre
- Description optionnelle
- Centré dans une Card

**data-loader.tsx**
- Wrapper composite pour gérer tous les états
- Affiche LoadingSpinner, ErrorMessage, EmptyState ou children
- API simple: loading, error, data, onRetry, emptyState props

**index.ts** — Export centralisé

### Tests (src/__tests__/hooks/)

**useQuery.test.ts**
- Test de succès (data + loading false)
- Test d'erreur
- Test du flag enabled
- Test des callbacks onSuccess/onError

## Architecture décisions

1. **Hook générique useQuery** : Réutilisable pour toute requête Tauri, similar à react-query/TanStack Query mais minimaliste.
2. **Hooks spécifiques par entité** : Typage fort (CemeteryDTO, PlotDTO, etc.) sans création de nouveaux DTOs.
3. **Async functions pour mutations** : Pas de hook useCommand car mutations sont simples (pas de cache).
4. **Composants d'état réutilisables** : LoadingSpinner, ErrorMessage, EmptyState sans dépendance externe.
5. **DataLoader wrapper** : Combine les 3 états (loading, error, empty) en une API unique.

## Types utilisés

**Entièrement typés TypeScript**:
- `CemeteryDTO`, `CreateCemeteryRequest`, `UpdateCemeteryRequest`
- `PlotDTO`, `CreatePlotRequest`, `UpdatePlotRequest`
- `ConcessionDTO`, `CreateConcessionRequest`, `UpdateConcessionRequest`
- `IndividualDTO`, `CreateIndividualRequest`, `UpdateIndividualRequest`
- `BurialDTO`, `CreateBurialRequest`
- `PlotStatus`, `ConcessionStatus`, `IndividualRole` (types énumérés)

**Zéro création de DTO** : Tous les types proviennent de `src/types/bindings.ts` généré depuis Rust.

## Limites acceptées

1. **Pas de mutation cache** : Les mutations retournent juste l'objet créé/updaté, ne mettent pas à jour le cache useQuery (prêt pour implémentation ultérieure).
2. **Pas de pagination** : API supporte `listCemeteries()` sans pagination; prêt pour ajout futur.
3. **Pas de polling/subscriptions** : useQuery fait une requête unique au mount/enable; prêt pour amélioration.
4. **Pas d'optimistic updates** : Mutations attendent la réponse backend; pattern classi que/safe.

## Tests

```bash
$ npx vitest run
 Test Files  4 passed (4)
      Tests  13 passed (13)
```

✅ TypeScript compilation: 0 error

## Fichiers modifiés

- package.json : aucun changement (dépendances déjà en place)
- src/types/bindings.ts : noté des ajouts cartographiques (PlotMapDTO, CemeteryMapDTO, etc.) pour MVP-07
- tsconfig.json : aucun changement
- vite.config.ts : setupFiles déjà inclus

## Prochaines étapes

1. **MVP-10/11** : Backend implémente les commandes Tauri complètes (remplacer les stubs)
2. **MVP-12** : Frontend crée les écrans métier (listes + fiches) en utilisant ces hooks
3. **MVP-13** : Frontend crée les écrans défunts + recherche
4. **Future** : Ajouter react-query/TanStack Query pour cache/mutations avancées si besoin

## Notes d'utilisation

### Exemple simple : Afficher une liste avec gestion d'état

```tsx
import { useCemeteries, LoadingSpinner, ErrorMessage, EmptyState } from "@/hooks";
import { Building2 } from "lucide-react";

export function CemeteryList() {
  const { data: cemeteries, loading, error, refetch } = useCemeteries();

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;
  if (!cemeteries?.length) {
    return <EmptyState icon={<Building2 />} title="Aucun cimetière" />;
  }

  return (
    <div>
      {cemeteries.map(c => (
        <div key={c.id}>{c.name}</div>
      ))}
    </div>
  );
}
```

### Exemple avec DataLoader (composant helper)

```tsx
import { useCemeteries, DataLoader, EmptyState } from "@/hooks";
import { Building2 } from "lucide-react";

export function CemeteryList() {
  const { data, loading, error, refetch } = useCemeteries();

  return (
    <DataLoader
      loading={loading}
      error={error}
      data={data}
      onRetry={refetch}
      emptyState={{ icon: <Building2 />, title: "Aucun cimetière" }}
    >
      <div>
        {data?.map(c => (
          <div key={c.id}>{c.name}</div>
        ))}
      </div>
    </DataLoader>
  );
}
```

### Exemple de mutation

```tsx
import { createCemeteryAsync } from "@/hooks";
import { useState } from "react";

export function CreateCemeteryForm() {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const created = await createCemeteryAsync({ name });
      console.log("Créé:", created);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <input value={name} onChange={e => setName(e.target.value)} />
      <button onClick={handleSubmit} disabled={loading}>
        Créer
      </button>
      {error && <ErrorMessage error={error} />}
    </div>
  );
}
```

## Validation

- ✅ TypeScript strict: 0 erreur
- ✅ Tests Vitest: 13/13 passing
- ✅ Compilation Cargo backend: 0 changement (isolation frontend)
- ✅ Pas de création de DTOs: utilise uniquement `bindings.ts`
- ✅ Tous les hooks sont typés et exportés centralement

## Readiness pour MVP-12+

Le frontend dispose maintenant de:
- ✅ Hooks réutilisables et typés
- ✅ Composants d'état (loading, error, empty)
- ✅ Mutations async simples
- ✅ Zéro dépendances personnalisées: prêt pour l'implémentation métier

**Verdict:** `FRONTEND_API_INTEGRATION_READY`
