# MVP-13 — Créer les écrans liste et fiche défunts, recherche globale

**Date:** 2026-06-16  
**Agent:** frontend  
**Statut:** ✅ Stabilisé  
**Dépend de:** MVP-02 ✅, MVP-06 ✅, MVP-11 ✅

## Objectif

Créer les écrans métier pour afficher et rechercher les défunts/personnes:
- Liste des défunts avec search local
- Fiche détail d'un défunt/personne
- Recherche globale améliorée (défunts + concessions)

## Tâches clés

- [x] Créer DefuntsPage avec search et filtrage
- [x] Créer DefuntDetailPage avec détails complets
- [x] Améliorer RecherchePage avec recherche par nom (défunts) et par ID (concessions)
- [x] Utiliser uniquement les hooks existants (useIndividuals, useSearchIndividuals, useConcessions)
- [x] Gérer loading/error/empty states de façon cohérente
- [x] Aucune création de DTO — utiliser uniquement les types générés

## Fichiers créés / modifiés

**Modifiés:**
- `src/pages/DefuntsPage.tsx` — Liste défunts avec search local
- `src/pages/DefuntDetailPage.tsx` — Créé en MVP-12
- `src/pages/RecherchePage.tsx` — Recherche globale améliorée
- `src/router.tsx` — Routes de détail

## Décisions prises

1. **Search local** — Les défunts sont filtrés côté client (sûr pour MVP, données limitées)
2. **Filtrage par rôle** — DefuntsPage affiche uniquement les individus avec role="deceased"
3. **Recherche globale** — Deux critères:
   - Recherche textuelle pour les noms (utilise useSearchIndividuals)
   - Recherche numérique pour les IDs de concession
4. **DataLoader wrapper** — Utilisé partout pour cohérence
5. **Contact affichage** — Affichage cliquable des emails et téléphones

## Implémentations principales

### Liste défunts (DefuntsPage.tsx)
- Recherche locale par nom
- Affichage des défunts avec role="deceased"
- Boutons "Détails" pour naviguer vers la fiche
- Statistiques en bas de page: total défunts, défunts avec contact
- États loading/error/empty gérés

### Fiche défunt (DefuntDetailPage.tsx)
- Affichage du nom et du rôle
- Informations de contact cliquables (email, téléphone)
- Données audit: créé le, modifié le
- Boutons d'action (Éditer, Imprimer, Supprimer) — stubs pour MVP
- Design cohérent avec ConcessionDetailPage

### Recherche globale (RecherchePage.tsx)
- Formulaire de recherche avec soumission
- Deux sections de résultats:
  - **Personnes:** utilise useSearchIndividuals pour recherche par nom
  - **Concessions:** filtre par ID numérique
- États loading/error/empty pour chaque section
- Affichage contextuel ("Aucun résultat pour...") en cas de recherche vide

## Types utilisés

- `IndividualDTO` (défunts, concessionnaires, ayants droit, contacts)
- `IndividualRole` type enum (deceased | concessionnaire | heir | contact)
- `ConcessionDTO` (pour résultats concessions)

**Zéro création de DTO** — tous les types proviennent de `bindings.ts`

## Tests

```bash
$ npx tsc --noEmit
✅ TypeScript: 0 errors

$ npx vitest run src/__tests__/hooks
✅ Hook tests: 5/5 passing
```

## Vérifications effectuées

- [x] TypeScript: 0 erreurs (après suppression imports inutilisés)
- [x] Tests hooks: 5/5 passant
- [x] Compilation sans erreur
- [x] DataLoader gère tous les états
- [x] Pas d'imports inutilisés
- [x] Types strictement typés

## Problèmes connus

- Actions sur les fiches (Éditer, Imprimer, etc.) sont des stubs
- Recherche globale ne supporte pas la recherche combinée (nom + ID)
- Pas de pagination vraie

## Prochaines étapes

1. MVP-14 — Intégrer cartographie réelle
2. MVP-25+ — Implémenter CRUD complet (formulaires d'édition)
3. MVP-26+ — Tests E2E pour les écrans métier

## Notes d'intégration

### Hooks utilisés
- `useIndividuals()` — Liste tous les individus
- `useSearchIndividuals(query)` — Recherche par nom
- `useIndividual(id)` — Fiche détail
- `useConcessions()` — Pour résultats de recherche globale

### Structure des données
- **Défunts** → individuals avec role="deceased"
- **Concessionnaires** → individuals avec role="concessionnaire"
- **Ayants droit** → individuals avec role="heir"
- **Contacts** → individuals avec role="contact"

## Validation

✅ Liste défunts affiche et recherche correctement
✅ Fiche défunt accessible via lien "Détails"
✅ Recherche globale trouve défunts et concessions
✅ Tous les états (loading, error, empty) gérés
✅ Types TypeScript générés utilisés exclusivement
✅ Pas de données mockées — données réelles de l'API backend
