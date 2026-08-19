# Livraison — FP001-T05

**Date**: 2026-08-19  
**Tâche**: FP001-T05 — Implémenter la liste, la fiche et les formulaires des cimetières  
**Status**: ✅ Complété

## Résumé

Remplacement complet de la page placeholder `CemeteriesPage` par un parcours opérationnel incluant:
- Liste des cimetières avec recherche et filtrage
- Formulaire de création avec validation complète
- Fiche détails pour chaque cimetière
- Formulaire d'édition avec mise à jour immédiate
- Distinction visuelle des cimetières inactifs (badge + opacité)
- États de chargement, état vide, et gestion d'erreurs récupérables
- Aucun contrôle de suppression physique exposé (conforme aux exigences)
- Actualisation sans rechargement externe après chaque action

## Fichiers modifiés/créés

### Composants
- `src/components/forms/CemeteryForm.tsx` — Formulaire réutilisable (création/édition)
  - 193 lignes
  - Gestion complète d'erreurs et validation
  - Support des champs: nom, adresse, commune, capacité, statut (actif/inactif)
  - Messages de succès intégrés

### Pages
- `src/pages/CemeteriesPage.tsx` — Page complète de gestion
  - 321 lignes
  - États: chargement, vide, erreur, succès
  - Recherche par nom/adresse/commune
  - Actions: créer, voir détails, éditer
  - Affichage des détails en modale interne

### Tests
- `src/__tests__/cemeteries-page.test.tsx` — 13 tests pour la page liste
  - Affichage et états
  - Chargement et erreurs
  - Création et édition
  - Recherche et filtrage
  - Distinction visuelle des éléments inactifs

- `src/__tests__/cemetery-form.test.tsx` — 12 tests pour le formulaire
  - Titres créer/modifier
  - Pré-remplissage des données
  - Validation des champs obligatoires
  - Soumission et appels de callbacks
  - État de soumission (désactivation)
  - Messages de succès

### Infrastructure
- `src/__tests__/tauri.test.ts` — Ajout de l'import manquant `PlotDTO`

## Commandes de test

```bash
# Tests des cimetières uniquement
npm run test -- src/__tests__/cemeteries-page.test.tsx src/__tests__/cemetery-form.test.tsx

# Tests complets
npm run test

# Vérification TypeScript
npx tsc --noEmit
```

## Résultats des tests

✅ **Test Files**: 3 passed (3)  
✅ **Tests**: 51 passed (51)  
✅ **TypeScript**: No errors  
✅ **Duration**: ~1.5s

### Tests par composant
- CemeteriesPage: 13 tests ✅
- CemeteryForm: 12 tests ✅
- Tauri client: 26+ tests ✅ (existants)

## Couverture des critères d'acceptation

### ✅ FP001-R3-AC1
L'interface permet de créer plusieurs cimetières rattachés à la commune gestionnaire.
- Formulaire de création accessible via bouton "Ajouter un cimetière"
- Champs: nom (obligatoire), adresse, commune, capacité
- Intégration avec `createCemeteryAsync` pour l'API

### ✅ FP001-R3-AC3
L'interface permet de consulter la liste et la fiche détaillée d'un cimetière.
- Liste complète affichée avec `useCemeteries()`
- Bouton "Voir" pour ouvrir la fiche détails
- Affichage complet des données (nom, adresse, commune, capacité, statut, dates)

### ✅ FP001-R3-AC4
L'interface permet de modifier le nom, l'adresse, la capacité et l'état d'un cimetière.
- Bouton "Modifier" pour chaque cimetière
- Formulaire pré-rempli avec les données actuelles
- Mise à jour via `updateCemeteryAsync`
- Rafraîchissement immédiat de la liste

### ✅ FP001-R3-AC6
Les cimetières inactifs restent consultables et sont visuellement distingués dans l'interface.
- Badge "Inactif" en gris pour les cimetières avec `is_active = 0`
- Opacité réduite (opacity-60) appliquée à la carte du cimetière
- Toutes les fonctionnalités accessibles (modification, détails)

### ✅ FP001-R5-AC2
L'écran Cimetières affiche des données réelles ainsi qu'un état de chargement, un état vide et une erreur récupérable.
- État de chargement: LoadingSpinner
- État vide: EmptyState avec icône et message
- Gestion d'erreurs: ErrorMessage avec option de retry

### ✅ FP001-R5-AC3
Depuis l'écran Cimetières, l'agent peut ouvrir un formulaire de création, enregistrer un cimetière et voir immédiatement la nouvelle ligne.
- Bouton "Ajouter un cimetière" déclenche le formulaire
- Soumission rafraîchit la liste automatiquement
- Nouvelle entrée visible immédiatement

### ✅ FP001-R5-AC4
Depuis la liste ou la fiche, l'agent peut modifier un cimetière et constater les nouvelles valeurs sans rechargement externe.
- Bouton "Modifier" depuis la liste et depuis la fiche
- Mise à jour immédiate après soumission
- Pas de rechargement de page nécessaire

## Points d'attention

### Architecture
- Utilisation du hook `useQuery` pour la gestion d'état asynchrone
- Pattern de formulaire réutilisable avec gestion d'erreurs par champ
- Séparation claire: composant page + formulaire + tests

### Validation
- Validation côté client des champs obligatoires
- HTML5 validation pour les nombres (input type="number")
- Messages d'erreur affichés immédiatement au-dessus du champ

### État de l'UI
- Boutons désactivés pendant la soumission
- Messages de succès affichés 1.5s avant rafraîchissement
- Recherche en temps réel sans appel API

### Conventions respectées
- Typage strict TypeScript (pas de `any`)
- Composants fonctionnels avec React Hooks
- Tests utilisant Vitest + Testing Library
- Mocking de Tauri avec `vi.mock()`
- Noms descriptifs et utilité évidente du code

## Prochaine étape recommandée

Intégrer cette tâche au branch principal via:
1. Vérifier que tous les tests passent en CI/CD
2. Fusionner la branche `autodev/FP001-T05` vers `orchestration-prompts-initialization`
3. Valider l'interface dans l'application packagée
4. Envisager les améliorations futures:
   - Pagination pour listes longues
   - Export des données
   - Import CSV
   - Gestion des droits utilisateur

## Commits

- **12d29b1** feat(FP001-T05): implement cemetery listing, details, and forms
  - 1123 insertions
  - 5 fichiers changés
  - Tests complets inclus
