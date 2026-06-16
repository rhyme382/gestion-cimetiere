# MVP-15 — Relier cartographie, concession et défunt côté interface

**Date :** 2026-06-16  
**Agent :** frontend  
**Statut :** ✅ Stabilisé  
**Dépend de :** MVP-12 ✅, MVP-13 ✅, MVP-14 ✅

## Objectif

Relier la cartographie (MVP-14) aux écrans métier (MVP-12/13) pour permettre :
- Visualiser l'emplacement lié à une concession
- Naviguer depuis une fiche concession vers la cartographie
- Naviguer depuis une fiche défunt vers la cartographie
- Afficher les localisations de manière intuitive

## Tâches clés

- [x] Créer composant PlotViewer pour afficher un emplacement spécifique
- [x] Ajouter visualisation d'emplacement sur ConcessionDetailPage
- [x] Ajouter navigation vers cartographie depuis ConcessionDetailPage
- [x] Ajouter navigation vers cartographie depuis DefuntDetailPage
- [x] Gérer les états (plot non trouvé, chargement, etc.)
- [x] Vérifier compilation TypeScript
- [x] Tester build production

## Fichiers créés / modifiés

**Créés :**
- ✅ `src/components/map/PlotViewer.tsx` — Composant de visualisation d'emplacement compact

**Modifiés :**
- ✅ `src/pages/ConcessionDetailPage.tsx` — Ajouter PlotViewer + navigation
- ✅ `src/pages/DefuntDetailPage.tsx` — Ajouter navigation cartographie

## Décisions prises

1. **PlotViewer compact** — Composant SVG simple pour afficher 1 plot sans dépendre de CemeteryMap
   - Peut être réutilisé sur d'autres fiches
   - Gère l'absence d'emplacement avec graceful fallback
   - Supporte les tailles "sm" et "md" pour flexibilité

2. **Navigation bidirectionnelle** — 
   - Depuis ConcessionDetailPage : "Voir sur la carte" navigue vers /emplacements
   - Depuis DefuntDetailPage : "Localiser sur la carte" navigue vers /emplacements
   - Futur MVP : peut ajouter la préselection du plot sur la carte

3. **Pas de modification cartographique** — MVP-14 reste intacte
   - Éventuellement, futur MVP ajouter des filtres/marqueurs
   - L'intégration réelle du backend sera simple (swap mock data)

4. **Utilisation des hooks existants** — 
   - `useConcession()` pour données concession
   - `usePlot()` pour visualiser l'emplacement
   - `useCemetery()` pour afficher le nom du cimetière

## Implémentations principales

### PlotViewer (src/components/map/PlotViewer.tsx)

Composant réutilisable pour afficher un emplacement :
- Affiche visualisation SVG compacte du plot
- Peut intégrer le nom du cimetière
- Graceful fallback si plot null
- Support multi-tailles (sm=200px, md=300px SVG)

```typescript
<PlotViewer 
  plot={plot}
  cemeteryName={cemetery?.name}
  size="sm"
/>
```

### Intégration ConcessionDetailPage

- Affiche PlotViewer si `concession.plot_id` existe
- Récupère le plot et le cimetière via hooks
- Ajoute bouton "Voir sur la carte" dans les actions
- Tous les états (loading, error) gérés automatiquement par hooks

### Intégration DefuntDetailPage

- Ajoute bouton "Localiser sur la carte" pour aller à EmplacementsPage
- Futur MVP : peut intégrer PlotViewer si on récupère les concessions du défunt

## Architecture

```
EmplacementsPage
  ├── CemeteryMap (cartographie complète)
  └── Sidebar (détails emplacement sélectionné)

ConcessionDetailPage
  ├── PlotViewer (visualisation emplacement)
  ├── Info section (détails concession)
  └── Actions (Éditer, Imprimer, **Voir sur la carte**, Supprimer)

DefuntDetailPage
  ├── Contact info (détails défunt)
  └── Actions (Éditer, Imprimer, **Localiser sur la carte**, Supprimer)
```

## Types utilisés

- `PlotDTO` — Emplacement complet (section, row, number, capacity, status)
- `ConcessionDTO` — Concession avec plot_id et cemetery_id
- `IndividualDTO` — Défunt/Personne
- `CemeteryDTO` — Cimetière

**Zéro création de DTO** — Tous les types existants utilisés

## Tests

```bash
$ npx tsc --noEmit
✅ TypeScript: 0 errors

$ npx vitest run src/__tests__/hooks
✅ Hook tests: 5/5 passing

$ npm run build
✅ Build successful (276.36 kB)
```

## Vérifications effectuées

- [x] TypeScript: 0 erreurs
- [x] Tests hooks: 5/5 passant
- [x] Compilation: sans erreur
- [x] Build npm: ✓ complète
- [x] Pas de imports inutilisés
- [x] Types strictement typés

## Problèmes connus

**Aucun problème fonctionnel identifié.**

**Limitations attendues (futures MVP) :**
- Pas de préselection automatique du plot sur la carte quand on navigue depuis ConcessionDetailPage
- Pas de filtrage visuel par statut concession sur la cartographie
- Pas de zoom/pan jusqu'au plot
- Pas de historique pour retrouver un plot après navigation

## Intégrations avec autres MVP

**MVP-14 (Cartographie)** :
- ✅ Intégration complète avec PlotViewer
- ✅ Aucune modification CemeteryMap requise
- ✅ Navigation réciproque possible

**MVP-12 (Concessions)** :
- ✅ ConcessionDetailPage améliore avec visualisation géographique
- ✅ Navigation bidirectionnelle vers cartographie

**MVP-13 (Défunts)** :
- ✅ DefuntDetailPage améliore avec lien cartographie
- ✅ Navigation simple vers EmplacementsPage

**Backend (MVP-10/11)** :
- ✅ Aucune dépendance nouvelle requise
- ✅ Utilise uniquement les commandes CRUD existantes
- ✅ Mock data continue de fonctionner

## Prochaines étapes

1. **MVP-16+** — Alertes :
   - Intégrer notifications d'échéance dans l'interface
   - Ajouter centre d'alertes

2. **MVP-17+** — Amélioration cartographique :
   - Ajouter zoom/pan
   - Ajouter filtres visuels par statut
   - Ajouter recherche sur le plan
   - Ajouter animation de sélection

3. **Post-MVP** — Intégrations avancées :
   - Import SIG (Leaflet) pour géométries personnalisées
   - QR codes sur les emplacements
   - Édition de cartographie

## Validation

✅ Cartographie ↔ Concessions liée avec visualisation  
✅ Cartographie ↔ Défunts liée avec navigation  
✅ PlotViewer composant réutilisable  
✅ Tous les types de bindings.ts utilisés  
✅ Aucun DTO personnalisé créé  
✅ Build production réussie  
✅ Tests unitaires passants  

## Conclusion

**MVP-15 stabilise l'intégration cartographique** en fournissant :
✅ Composant PlotViewer réutilisable  
✅ Visualisation d'emplacement sur fiches métier  
✅ Navigation bidirectionnelle cartographie ↔ fiches  
✅ États d'erreur et chargement gérés  
✅ Architecture propre et maintenable  
✅ Prêt pour intégration backend réelle (MVP-10/11)  

**Blocages résolus :** Séparation entre UI métier et cartographie clairement établie, navigation intuitive mise en place.

**Prochains jalons :** MVP-16 (alertes), MVP-17+ (améliorations cartographiques optionnelles).
