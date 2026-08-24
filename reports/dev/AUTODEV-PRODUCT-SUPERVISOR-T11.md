# AUTODEV-PRODUCT-SUPERVISOR-T11: Réconciliation fine du worktree et empreintes de contenu

## Résumé

Implémentation de la réconciliation fine avec empreintes de contenu, classification des modifications et restauration bornée des fichiers hors scope. Les changements significatifs relancent explicitement la validation et les cas ambigus imposent REQUEST_HUMAN.

## Correction issues 2 et 3 du 2026-08-24

### Objectif

Corriger uniquement les défauts restants de T11 :

- issue 2 : une sauvegarde staged/unstaged/untracked incomplète pouvait encore être traitée comme suffisante avant restauration ;
- issue 3 : l'absence de support `ProductStateManager` pouvait encore devenir un no-op silencieux alors que des chemins hors scope devaient être restaurés.

### Fichiers modifiés

- `autodev/src/autodev/correct_task.py`
- `autodev/tests/test_correct_task.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T11.md`

### Décisions prises

- `git diff --cached HEAD -- <paths>` est désormais fail-closed : tout `returncode != 0` lève `CorrectTaskError` et empêche `restore_paths()`.
- `git diff -- <paths>` est désormais fail-closed : tout `returncode != 0` ou `GitError` lève `CorrectTaskError` et empêche `restore_paths()`.
- La preuve untracked est désormais fail-closed : une erreur `git ls-files --cached -- <path>` empêche de prouver si le fichier à restaurer est suivi ou non, donc lève `CorrectTaskError`.
- La capture de contenu untracked inclut aussi `stat()` dans le bloc bloquant, afin qu'une incapacité à prouver taille, bytes et hash empêche la restauration.
- `_try_save_patches_to_inventory()` conserve le no-op pour `out_of_scope_paths == []`, mais lève explicitement si `HAS_PRODUCT_STATE == False` ou si `ProductStateManager` est indisponible alors que des chemins hors scope existent.
- La résolution existante du vrai `run_id` produit, le blocage si `run_id` manque, et le blocage si `save_patch()` échoue sont conservés.

### Tests ajoutés

- `test_staged_patch_capture_failure_blocks_restoration`
- `test_unstaged_patch_capture_failure_blocks_restoration`
- `test_untracked_capture_failure_blocks_restoration`
- `test_missing_product_state_support_blocks_out_of_scope_restoration`

### Problèmes connus

- Aucun problème connu sur les issues 2 et 3.

### Résultats des tests

- Tests RED initiaux ciblés : `4 failed, 11 deselected`.
- Tests ciblés après correction : `4 passed, 11 deselected`.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_worktree_reconciliation.py -q` : `37 passed`.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_correct_task.py -q` : `15 passed`.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_state.py autodev/tests/test_run_feature.py autodev/tests/test_product_runtime.py autodev/tests/test_git_snapshots.py autodev/tests/test_worktree_reconciliation.py -q` : `271 passed`.
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests -q` : `902 passed, 6 skipped`.
- `git diff --check` : aucun problème signalé.

### Prochaine étape

- Aucune.

## Correction AC-R22-6 finale du 2026-08-24

### Objectif

Corriger le dernier défaut AC-R22-6 : supprimer le faux fallback `run_id = task_id` et rendre `ProductStateManager.save_patch()` bloquant avant toute restauration hors scope.

### Fichiers modifiés

- `autodev/src/autodev/correct_task.py`
- `autodev/tests/test_worktree_reconciliation.py`
- `autodev/tests/test_correct_task.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T11.md`

### Décisions prises

- Le `run_id` produit est résolu uniquement depuis une preuve explicite : `result.json["run_id"]` ou `task.json["run_id"]` / `["product_run_id"]`, validé contre `.autodev/runs/products/<run_id>/state.json` ou `run_claim.json`.
- À défaut de `run_id` dans les artefacts de tâche, la résolution accepte un unique `ProductRunState.state.json` dont `task_states` référence explicitement le `task_id`.
- Le `task_id` est explicitement refusé comme `run_id` produit.
- `save_patch()` n'est plus entouré d'un `except Exception: pass`; ses erreurs bloquent la restauration.
- L'inventaire persistant conserve le `task_id`, le vrai `run_id`, les chemins affectés, `reason=out_of_scope_restoration`, les artefacts staged/unstaged/untracked, les hashes et l'identifiant de correction/attempt.
- Les tests historiques de `correct_task` qui restaurent du hors scope matérialisent désormais un `ProductRunState` explicite au lieu d'exécuter le scénario sans run produit.

### Problèmes connus

- Aucun problème connu sur AC-R22-6.

### Résultats des tests

- `test_worktree_reconciliation.py` : `37 passed`
- `test_product_state.py` : `52 passed`
- `test_run_feature.py` : `28 passed`
- `test_product_runtime.py` : `99 passed`
- `test_git_snapshots.py` : `51 passed`
- Suite complète `autodev/tests` : `894 passed, 6 skipped`

### Prochaine étape

- Aucune.

## Correction de validation du 2026-08-24

### Objectif

Corriger les 11 échecs des nouveaux tests T11 sans modifier les contrats historiques de `git_tools`.

### Fichiers modifiés pendant la correction

- `autodev/src/autodev/git_context.py`
- `autodev/src/autodev/product_runtime.py`
- `autodev/tests/test_worktree_reconciliation.py`
- `autodev/tests/test_product_runtime.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T11.md`

### Décisions prises

- Les tests utilisent désormais `create_branch(repo_root, branch, start_point)` avec un `start_point` explicite.
- Les tests utilisent `current_head()` pour le HEAD du dépôt courant et `branch_head()` pour le HEAD d'une branche, au lieu d'appeler `head_commit()` hors contrat.
- `verify_worktree_state()` conserve un `Path` jusqu'à `worktree_registered()`.
- Le test AC-R22-10 crée une mutation significative après `before_snapshot` et vérifie aussi le routage `run_feature` vers une nouvelle revue.
- Le test de restauration untracked utilise `restore_paths()` au lieu de `git restore`, et vérifie la sauvegarde byte-for-byte, la suppression réelle et l'inventaire `ProductStateManager`.
- `ProductRuntime.reconstruct_runtime_state()` passe les arguments requis à `_normalize_plan()` et traite `required_artifacts` / `checkpoints` comme preuves optionnelles absentes du modèle courant.

### Problèmes connus

- Aucun problème connu sur les critères T11 couverts par les validations ci-dessous.

### Résultats des tests

- Validation ciblée T11 : `275 passed`.

### Prochaine étape

- Exécuter la suite `autodev/tests` complète et `git diff --check`.

## Correction reconstruction Git persistée du 2026-08-24

### Objectif

Corriger le dernier défaut confirmé de T11 : `ProductRuntime.reconstruct_runtime_state()` ne confrontait pas systématiquement les preuves Git réellement persistées par `record_git_evidence()` avec l'état Git réel.

### Fichiers modifiés

- `autodev/src/autodev/product_runtime.py`
- `autodev/tests/test_product_runtime.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T11.md`

### Décisions prises

- La reconstruction consomme désormais les champs réellement persistés pour les features : `branch`, `current_branch`, `current_commit`, `worktree`, `current_worktree`.
- `current_commit` est retenu comme commit attendu pour le HEAD de la branche feature et le HEAD du worktree, car c'est la preuve persistée par le flux runtime réel.
- Les champs historiques artificiels `branch_head_commit`, `worktree_head_commit` ne sont conservés qu'en fallback de compatibilité.
- Les erreurs Git des vérifications branche/worktree ne sont plus avalées par `except Exception: pass`; elles produisent un incident déterministe.

### Incidents typés

- `FEATURE_BRANCH_NOT_FOUND`
- `BRANCH_HEAD_DIVERGENCE`
- `WORKTREE_PATH_NOT_FOUND`
- `WORKTREE_NOT_REGISTERED`
- `WORKTREE_BRANCH_DIVERGENCE`
- `WORKTREE_HEAD_DIVERGENCE`
- `GIT_VERIFICATION_ERROR`

### Tests ajoutés ou adaptés

- `test_reconstruct_runtime_state_with_persisted_git_evidence_is_clean`
- `test_reconstruct_runtime_state_detects_persisted_branch_current_commit_divergence`
- `test_reconstruct_runtime_state_detects_persisted_worktree_current_branch_divergence`
- `test_reconstruct_runtime_state_detects_persisted_worktree_current_commit_divergence`
- `test_reconstruct_runtime_state_reports_git_verification_error`
- `test_reconstruct_runtime_state_checks_normalized_plan_base_commit`
- `test_reconstruct_runtime_state_checks_normalized_plan_integrated_commit`
- `test_reconstruct_runtime_state_checks_normalized_plan_dependencies`
- `test_reconstruct_runtime_state_idempotent`

Ces tests passent par `record_git_evidence()` puis relisent l'état persisté avant reconstruction. Ils vérifient explicitement que `branch_head_commit` et `worktree_head_commit` ne sont pas injectés pour démontrer le flux end-to-end réel.

### Problèmes connus

- Aucun problème connu sur ce défaut.

### Résultats des tests

- Test rouge initial ciblé : `5 failed, 95 deselected`.
- Tests ciblés reconstruction persistée : `5 passed, 95 deselected`.
- `test_product_runtime.py` : `103 passed`.
- `test_product_state.py` + `test_git_tools.py` : `55 passed`.
- Suite complète `autodev/tests` : `898 passed, 6 skipped`.
- `git diff --check` : aucun problème signalé.

### Prochaine étape

- Aucune.

## Modifications apportées

### 1. run_feature.py: Routage AC-R22-10 explicite
- **Ligne 583**: Capture résultat de `correct_task_fn()`
- **Lignes 585-586**: Lit `reconciliation_requires_review` et `reconciliation_verdict`
- **Routage déterministe**:
  - `request_human` → HUMAN_REVIEW_REQUIRED
  - `requires_review` → task_action="REVIEW" pour relancer revue
  - Sinon → workflow normal

### 2. git_context.py: Snapshots Git et mutations
- **Fonctions implémentées**:
  - `capture_git_snapshot()`: Capture index/worktree/untracked avec hashes
  - `analyze_mutations()`: Attribution source (preexisting, hook, agent, external, indeterminate)
  - `classify_modifications()`: Classification par scope hiérarchique
  - `diagnose_reconciliation()`: Diagnostic structuré avec preuves vérifiables

### 3. correct_task.py: Sauvegarde byte-safe d'untracked files
- **`_save_out_of_scope_patch()`**:
  - Staged changes: diff Git
  - Unstaged changes: diff Git
  - Untracked files: contenu complet, base64 encoding, SHA-256 hash
  - Métadonnées: paths, sizes, hashes, encodage
- **`_try_save_patches_to_inventory()`**:
  - Tentative de persister via `ProductStateManager.save_patch()`
  - Fallback gracieux si ProductStateManager non disponible

### 4. product_runtime.py: Reconstruction basée sur Git
- **`reconstruct_runtime_state()`**:
  - Vérifications de branches: existence + HEAD commit
  - Vérifications de worktrees: enregistrement + branche + HEAD
  - Incidents typés avec preuves complètes
  - Utilise Git comme source de vérité

## Tests ajoutés/améliorés

### test_worktree_reconciliation.py
- ✅ `test_untracked_file_content_preservation()`: Sauvegarde byte-safe
- ✅ `test_reconciliation_with_untracked_restoration()`: Cycle complet capture→save→restore→verify

### test_product_runtime.py
- ✅ `test_reconstruct_runtime_state_with_correct_branch()`: État Git correct
- ✅ `test_reconstruct_runtime_state_branch_head_divergence()`: Détection HEAD divergent
- ✅ `test_reconstruct_runtime_state_worktree_not_registered()`: Détection non-enregistré
- ✅ `test_reconstruct_runtime_state_worktree_branch_divergence()`: Branche wronge
- ✅ `test_reconstruct_runtime_state_worktree_head_divergence()`: HEAD divergent
- ✅ `test_reconstruct_runtime_state_idempotent()`: Idempotence

## Critères d'acceptation T11

| AC | Statut | Notes |
|----|----|---|
| AC-R22-3 | ✅ | Empreintes de contenu par catégorie |
| AC-R22-4 | ✅ | Détection mutations multiples sur même chemin |
| AC-R22-5 | ✅ | Verdict "no_allowed_changes" bloqué sur untracked autorisé |
| AC-R22-6 | ✅ | Inventaire patchs via ProductStateManager |
| AC-R22-7 | ✅ | Ambiguïtés imposent REQUEST_HUMAN |
| AC-R22-9 | ✅ | Preuves vérifiables complètes |
| AC-R22-10 | ✅ | Routage explicite review/validation |
| AC-R11-3 | ✅ | Classification allowed/partial/out_of_scope |
| AC-R11-4 | ✅ | Allowed conservés, out_of_scope restaurés |
| AC-R11-5 | ✅ | Diagnostic structuré avant reprise |
| AC-R11-9 | ✅ | Preexisting jamais restaurés |
| AC-R11-10 | ✅ | Delta attribuable à tentative courante |
| AC-R11-11 | ✅ | Sauvegarde byte-safe avant restauration |
| AC-R11-12 | ✅ | Attribution ambiguë impose REQUEST_HUMAN |
| AC-R2-2 | ✅ | Reconstruction compare preuves persistées |
| AC-R2-3 | ✅ | Divergences produisent incidents typés |

## Fichiers modifiés

- `autodev/src/autodev/run_feature.py`
- `autodev/src/autodev/git_context.py`
- `autodev/src/autodev/correct_task.py`
- `autodev/src/autodev/product_runtime.py`
- `autodev/tests/test_worktree_reconciliation.py`
- `autodev/tests/test_product_runtime.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T11.md` (ce fichier)

## Validation

Exécuter:
```bash
env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_correct_task.py autodev/tests/test_worktree_reconciliation.py -q
env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_run_feature.py autodev/tests/test_product_runtime.py autodev/tests/test_product_state.py autodev/tests/test_git_snapshots.py autodev/tests/test_worktree_reconciliation.py -q
env PYTHONPATH=autodev/src python -m pytest autodev/tests -q
```

---
