# Rapport de Développement — FP-004-T04: Câbler les repositories et commandes Tauri

## Résumé exécutif

La tâche FP-004-T04 a été corrigée et complétée avec succès. Elle avait pour objectif de câbler les repositories et commandes Tauri pour lire la hiérarchie des niveaux d'un cimetière (sections, carrés, rangées) et le chemin complet d'un emplacement.

**État final après correction:**
- ✅ Tous les critères d'acceptation atteints, incluant les trois issues majeures
- ✅ 16 tests d'intégration passent (incluant 5 nouveaux tests de NotFound différenciés)
- ✅ 177 tests au total passent (aucune régression)
- ✅ Chemin hiérarchique complet avec identifiants, codes et libellés
- ✅ Erreurs NotFound différenciées pour chaque niveau hiérarchique
- ✅ Persistance du chemin hiérarchique complet vérifiée après close/reopen

### Corrections apportées

**Issue 1 — Identifiants manquants du chemin hiérarchique:**
- `HierarchicalPathDTO` enrichi avec `section_id`, `square_id`, `row_id` (Option<i64>)
- `get_hierarchical_path()` sélectionne et retourne tous les identifiants
- Tests de DTO mis à jour

**Issue 2 — NotFound non-différencié pour parents inexistants:**
- `list_sections()` valide l'existence du cimetière, retourne NotFoundKind::Cemetery
- `list_squares()` valide l'existence de la section, retourne NotFoundKind::Section
- `list_rows()` valide l'existence du carré, retourne NotFoundKind::Square
- 5 nouveaux tests de validation des NotFound différenciés

**Issue 3 — Test de persistance incomplet:**
- Nouveau test `test_hierarchical_path_persistence_across_close_reopen()` qui:
  - Crée une hiérarchie complète (section → square → row)
  - Crée un emplacement lié à cette rangée
  - Ferme et réouvre la base de données
  - Vérifie la relisibilité du chemin complet avec tous les identifiants

---

## Modifications effectuées

### 1. Enrichissement de PlotRepository (`src-tauri/src/db/repositories/plot_repo.rs`)

#### Imports
- Ajout de `HierarchicalPathDTO` et `NotFoundKind` pour gérer les chemins hiérarchiques et les erreurs typées

#### Méthodes d'accès à la hiérarchie

**`list()`** — Énumère les emplacements d'un cimetière
- Maintient la compatibilité existante (tri par section, rangée, numéro)
- Enrichit chaque PlotDTO avec le chemin hiérarchique via `get_hierarchical_path()`
- Peuple l'`administrative_reference` depuis la base de données

**`get()`** — Récupère un emplacement par ID
- Enrichit le PlotDTO avec le chemin hiérarchique
- Gère les erreurs `NotFound` avec le type `NotFoundKind::Plot` pour une différenciation au niveau de l'API

**`get_hierarchical_path(id)`** (nouveau)
- Récupère le chemin complet d'un emplacement (section, carré, rangée avec codes et libellés)
- Retourne `None` si l'emplacement n'a pas de `row_id` établi
- Utilise une requête LEFT JOIN pour traverser la hiérarchie

**`list_sections(cemetery_id)`** (nouveau, enrichi)
- Vérifie d'abord l'existence du cimetière → retourne NotFoundKind::Cemetery si absent
- Si le cimetière existe, liste les sections actives
- Retourne les triplets (id, normalized_code, display_label)
- Triées par `display_order` et `normalized_code`
- Retourne une liste vide si le cimetière existe mais n'a pas de sections

**`list_squares(section_id)`** (nouveau, enrichi)
- Vérifie d'abord l'existence de la section → retourne NotFoundKind::Section si absente
- Si la section existe, liste les carrés (squares) actifs
- Retourne les triplets (id, normalized_code, display_label)
- Retourne une liste vide si la section existe mais n'a pas de carrés

**`list_rows(square_id)`** (nouveau, enrichi)
- Vérifie d'abord l'existence du carré → retourne NotFoundKind::Square si absent
- Si le carré existe, liste les rangées (rows) actives
- Retourne les triplets (id, normalized_code, display_label)
- Retourne une liste vide si le carré existe mais n'a pas de rangées

#### Méthodes de validation hiérarchique

**`get_section(section_id, cemetery_id)`** (nouveau)
- Récupère une section avec validation du cimetière parent
- Lève `NotFoundKind::Section` si non trouvée

**`get_square(square_id, section_id)`** (nouveau)
- Récupère un carré avec validation de la section parent
- Lève `NotFoundKind::Square` si non trouvé

**`get_row(row_id, square_id)`** (nouveau)
- Récupère une rangée avec validation du carré parent
- Lève `NotFoundKind::Row` si non trouvée

**`cemetery_exists(cemetery_id)`** (nouveau)
- Vérifie l'existence d'un cimetière

### 2. Extension des commandes Tauri (`src-tauri/src/commands/plot.rs`)

Trois nouvelles commandes ont été ajoutées pour exposer les lectures de hiérarchie au client:

- **`list_sections(cemetery_id)`** — Énumère les sections d'un cimetière
- **`list_squares(section_id)`** — Énumère les carrés d'une section
- **`list_rows(square_id)`** — Énumère les rangées d'un carré

Ces commandes suivent les mêmes patterns de gestion des erreurs que les commandes existantes.

### 3. Enrichissement du DTO (`src-tauri/src/dto/plot.rs`)

**`HierarchicalPathDTO`**
- Ajout des identifiants: `section_id: Option<i64>`, `square_id: Option<i64>`, `row_id: Option<i64>`
- Conservation des codes et labels existants: `section_code`, `section_label`, `square_code`, `square_label`, `row_code`, `row_label`
- Ajout du trait `PartialEq` pour permettre les assertions d'égalité dans les tests
- Implémentation de `Default` avec tous les champs à `None`

**`PlotDTO`**
- Les champs `administrative_reference` et `hierarchical_path` sont peuplés par `list()` et `get()` du repository
- `hierarchical_path` inclut les identifiants des trois niveaux (section, carré, rangée)

---

## Spécifications métier atteintes

### R3 — Traçabilité de la hiérarchie
✅ **FP004-R3-AC5** — La hiérarchie complète d'un emplacement est lisible avec les identifiants, codes et libellés de sa section, de son carré et de sa rangée.
- Le chemin hiérarchique est accessible via `PlotDTO.hierarchical_path`
- Structure: `HierarchicalPathDTO` avec tous les codes et labels normalisés

### R5 — Contrats d'interface
✅ **FP004-R5-AC3** — Les repositories permettent de relire les niveaux d'un cimetière et le chemin complet d'un emplacement.
- `PlotRepository::list_sections()`, `list_squares()`, `list_rows()` pour naviguer la hiérarchie
- `PlotRepository::get_hierarchical_path()` pour le chemin complet
- Commandes Tauri correspondantes exposées

✅ **FP004-R5-AC4** — Une demande portant sur un cimetière, une section, un carré, une rangée ou un emplacement inexistant produit une erreur `NotFound` différenciée.
- Erreurs typées via `AppError::with_kind()` et `NotFoundKind` enum
- Sérialisation JSON expose le type d'erreur spécifique (CEMETERY_NOT_FOUND, SECTION_NOT_FOUND, etc.)

---

## Tests intégrés

### Suite: `integration_plot.rs`

16 tests couvrent la fonctionnalité, incluant 5 nouveaux tests de validation NotFound:

**Tests de chemin hiérarchique et référence administrative:**
1. **`test_plot_has_administrative_reference`** — Vérifie que l'administrative_reference est auto-générée (EMP-{id})
2. **`test_plot_hierarchical_path_none_without_row_id`** — Confirme que hierarchical_path est None pour les emplacements sans row_id
3. **`test_administrative_reference_persistence_across_close_reopen`** — Valide la persistence après fermeture/réouverture

**Tests de navigation hiérarchique:**
4. **`test_list_sections_for_cemetery`** — Valide l'énumération des sections
5. **`test_list_squares_for_section`** — Valide l'énumération des carrés
6. **`test_list_rows_for_square`** — Valide l'énumération des rangées

**Tests des erreurs NotFound différenciées (nouveaux):**
7. **`test_list_sections_with_nonexistent_cemetery`** — Retourne NotFoundKind::Cemetery pour cimetière inexistant
8. **`test_list_sections_with_existing_cemetery_no_sections`** — Retourne liste vide si cimetière existe mais pas de sections
9. **`test_list_squares_with_nonexistent_section`** — Retourne NotFoundKind::Section pour section inexistante
10. **`test_list_rows_with_nonexistent_square`** — Retourne NotFoundKind::Square pour carré inexistant
11. **`test_get_plot_not_found_with_typed_error`** — Vérifie NotFoundKind::Plot pour emplacement inexistant

**Test de persistance avec hiérarchie (nouveau):**
12. **`test_hierarchical_path_persistence_across_close_reopen`** — Valide que le chemin hiérarchique complet (avec identifiants) reste lisible après close/reopen

**Tests existants préservés:**
- 4 autres tests de workflow, création et mise à jour (continuent de passer)

### Résultats

```
running 16 tests
test result: ok. 16 passed; 0 failed

running 7 tests (integration_tauri_commands)
test result: ok. 7 passed; 0 failed

Tous les tests: 177/177 passent
```

---

## Considérations architecturales

### Hiérarchisation automatique vs. explicite

**Observation:** Lors de la création d'emplacements APRÈS l'exécution initiale de la migration, ils n'ont pas automatiquement de `row_id` établi. Cela est le comportement attendu car:

1. La migration crée la hiérarchie et lie les emplacements existants
2. Les nouveaux emplacements créés post-migration sont dans un état "non classé"
3. L'affectation à une rangée reste une opération explicite

Les tests reflètent ce modèle: `hierarchical_path` est `None` pour les emplacements sans `row_id`, ce qui est correct.

### Gestion des erreurs différenciées

Le système utilise `NotFoundKind` enum pour distinguer les types d'entités non trouvées. Cela permet au client de:
- Afficher des messages d'erreur spécifiques par type d'entité
- Prendre des décisions métier basées sur le type d'erreur
- Logger et auditer avec précision

---

## Chemins autorisés modifiés

Tous les changements respectent les contraintes:

- ✅ `src-tauri/src/db/repositories/plot_repo.rs` — Enrichi avec nouvelles méthodes
- ✅ `src-tauri/src/commands/plot.rs` — Enrichi avec nouvelles commandes
- ✅ `src-tauri/src/dto/plot.rs` — Enrichi avec `PartialEq` sur DTO
- ✅ `src-tauri/tests/integration_plot.rs` — Tests ajoutés

Aucun autre chemin n'a été modifié.

---

## Vérifications d'intégrité

### Compilation
```
cargo check -p gestion-cimetiere
✅ Succès — Aucune erreur ou avertissement
```

### Tests d'intégration
```
cargo test -p gestion-cimetiere --test integration_plot
✅ 16/16 tests passent (incluant 5 nouveaux tests de NotFound différenciés + persistance)

cargo test -p gestion-cimetiere --test integration_tauri_commands
✅ 7/7 tests passent
```

### Suite complète
```
cargo test -p gestion-cimetiere
✅ 177/177 tests passent
```

### Aucune régression
- Tous les tests existants continuent de passer
- Les nouvelles méthodes suivent les patterns établis
- L'API Tauri reste rétro-compatible

---

## Impact utilisateur

### API TypeScript (générée via Specta)

Les nouveaux types TypeScript sont automatiquement générés:

```typescript
// Nouveaux types d'API
list_sections(cemetery_id: number): Promise<Array<[number, string, string]>>
list_squares(section_id: number): Promise<Array<[number, string, string]>>
list_rows(square_id: number): Promise<Array<[number, string, string]>>

// PlotDTO enrichi
interface PlotDTO {
  hierarchical_path?: HierarchicalPathDTO
  administrative_reference?: string
}

interface HierarchicalPathDTO {
  section_id?: number
  section_code?: string
  section_label?: string
  square_id?: number
  square_code?: string
  square_label?: string
  row_id?: number
  row_code?: string
  row_label?: string
}

// Erreurs typées
interface ApiErrorResponse {
  error_type: "SECTION_NOT_FOUND" | "SQUARE_NOT_FOUND" | "ROW_NOT_FOUND" | ...
  message: string
}
```

---

## Prochaines étapes possibles

Pour une intégration complète de FP-004, il serait possible:

1. **FP-004-T05** — Implémenter le CRUD complet des sections, carrés et rangées
2. **FP-004-T06** — Ajouter l'assignation automatique des emplacements à la hiérarchie
3. **FP-004-T07** — Implémenter des tests E2E du flux UI de navigation hiérarchique
4. **FP-004-T08** — Optimiser les requêtes de lecture hiérarchique avec des indexations supplémentaires

---

## Conclusion

FP-004-T04 a été implémentée avec succès. Le système peut maintenant:

- ✅ Lire les niveaux hiérarchiques d'un cimetière
- ✅ Récupérer le chemin complet d'un emplacement
- ✅ Exposer cette fonctionnalité via des commandes Tauri
- ✅ Fournir des erreurs typées et différenciées
- ✅ Maintenir la persistance après close/reopen de base de données

La fonctionnalité est prête pour intégration et test en environnement de développement complet.
