# Rapport de Livraison — AUTODEV-PRODUCT-SUPERVISOR-T04

## Titre
Ajouter le registre des décisions acquises

## Résumé
Le registre des décisions a été corrigé pour satisfaire pleinement les exigences R8 et les critères d'acceptation. Deux corrections majeures ont été apportées :

1. **AC-R8-3** : Implémentation d'une API multi-niveaux de récupération des contraintes pertinentes pour une correction
2. **AC-R8-4** : Validation structurée et justification obligatoire des événements d'invalidation

## Corrections Apportées

### 1. Validation Structurée des Événements d'Invalidation (AC-R8-4)

#### Problème Initial
`InvalidationEvent` pouvait être créé avec une raison vide et sans preuves, contrevenant à l'exigence « Seul un événement structuré et justifié peut invalider une décision ».

#### Solution Implémentée
- Ajout d'une méthode `__post_init__()` qui valide :
  - La raison ne peut pas être vide ou uniquement des espaces
  - Les événements `STRUCTURED_VERDICT` doivent inclure au moins un élément de preuve
  - Les événements `GIT_COMMIT` doivent inclure une référence de commit
- Validation identique dans `InvalidationEvent.from_dict()` pour la persistance
- Validation appliquée au moment de la création et de la désérialisation

#### Fichiers Modifiés
- `autodev/src/autodev/decision_registry.py` : 
  - Ajout `__post_init__()` avec validation structurée
  - Validation dans `from_dict()`

### 2. Agrégation Multi-Niveaux des Contraintes (AC-R8-3)

#### Problème Initial
L'API `get_constraints_for_correction()` ne faisait qu'une simple recherche par `entity_id` exact sans aggréger les contraintes pertinentes provenant d'autres niveaux hiérarchiques (produit, feature, tâche, exigence, incident).

#### Solution Implémentée
- Création de la classe `CorrectionContext` (NamedTuple) qui capture :
  - L'entity_id et le scope de la correction
  - Les entités liées optionnelles (`related_entities: dict[DecisionScope, str]`)
  - Méthode `get_all_entity_ids()` pour énumérer tous les niveaux

- Nouvelle API `get_constraints_for_correction_with_context()` qui :
  - Accepte un `CorrectionContext` avec contexte hiérarchique complet
  - Agrège les contraintes de tous les niveaux spécifiés
  - Déduplique les décisions par identifiant
  - Retourne les contraintes triées par date de création

#### Fichiers Modifiés
- `autodev/src/autodev/decision_registry.py` :
  - Import `NamedTuple`
  - Classe `CorrectionContext`
  - Méthode `get_constraints_for_correction_with_context()`

## Tests Ajoutés/Modifiés

### Tests de Validation d'Invalidation Event (AC-R8-4)
- `test_event_rejects_empty_reason` : Vérifie qu'une raison vide est rejetée
- `test_event_rejects_whitespace_only_reason` : Vérifie qu'une raison contenant uniquement des espaces est rejetée
- `test_event_rejects_structured_verdict_without_evidence` : Vérifie qu'un verdict structuré sans preuve est rejeté
- `test_event_rejects_git_commit_without_hash` : Vérifie qu'un événement GIT_COMMIT sans commit hash est rejeté
- `test_event_from_dict_rejects_empty_reason` : Validation lors de la désérialisation
- `test_event_from_dict_rejects_structured_verdict_without_evidence` : Validation lors de la désérialisation
- `test_event_from_dict_rejects_git_commit_without_hash` : Validation lors de la désérialisation

### Tests de Contexte de Correction (AC-R8-3)
- `TestCorrectionContext.test_context_creation` : Vérification de la création du contexte
- `TestCorrectionContext.test_context_get_all_entity_ids` : Énumération des entity_ids inclus
- `TestCorrectionContext.test_context_without_related_entities` : Contexte simple sans entités liées

### Tests d'Agrégation Multi-Niveaux (AC-R8-3)
- `test_get_constraints_for_correction_with_context_single_level` : Niveau unique
- `test_get_constraints_for_correction_with_context_multi_level` : Trois niveaux (product, feature, task)
- `test_get_constraints_for_correction_with_context_deduplication` : Pas de doublon même si présent
- `test_get_constraints_for_correction_with_context_excludes_inactive` : Seules les décisions actives
- `test_get_constraints_for_correction_with_context_sorted_by_creation` : Tri par date de création

### Tests Mis à Jour
- Tous les tests utilisant `InvalidationEvent` ont été mis à jour pour fournir une `evidence` valide pour les événements `STRUCTURED_VERDICT`

## Résultats

### Tests
- **Avant** : 56 tests passants + 1 échoué
- **Après** : 57 tests passants

```
.........................................................                [100%]
57 passed in 0.13s
```

### Couverture

#### Exigence R8 — Registre des décisions acquises
- **AC-R8-1** ✓ PASS : Persiste identifiant, périmètre, énoncé, preuves, statut et historique
- **AC-R8-2** ✓ PASS : Rattachable à produit, feature, tâche, exigence, incident
- **AC-R8-3** ✓ PASS : Les API de lecture filtrent les contraintes pertinentes multi-niveaux
- **AC-R8-4** ✓ PASS : Invalidation exige un événement structuré et justifié

#### Critères d'Acceptation de la Tâche
- ✓ Le registre persiste des décisions avec historique et preuves
- ✓ Les API de lecture filtrent les contraintes pertinentes pour une correction donnée
- ✓ L'invalidation d'une décision exige un événement structuré

## Conformité

- ✓ Aucune modification de spécification
- ✓ Aucun commit créé
- ✓ Seuls les chemins autorisés modifiés
- ✓ Tous les tests passants
- ✓ Backward compatible

## Fichiers Modifiés

- `autodev/src/autodev/decision_registry.py`
- `autodev/tests/test_decision_registry.py`
