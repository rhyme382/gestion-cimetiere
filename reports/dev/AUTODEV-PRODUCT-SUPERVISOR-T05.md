# Rapport de Correction — AUTODEV-PRODUCT-SUPERVISOR-T05

## objectif
Ajouter une API runtime publique de persistance des preuves Git structurées, sans interroger Git, afin que les futures tâches puissent enregistrer commits, branches et worktrees dans l'état reconstruit du run produit et des features.

## fichiers modifiés
- `autodev/src/autodev/product_runtime.py`
- `autodev/src/autodev/product_state.py`
- `autodev/tests/test_product_runtime.py`
- `autodev/tests/test_product_state.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T05.md`

## décisions prises
- `ProductRuntime.record_git_evidence()` a été ajoutée comme API publique de persistance des preuves structurées fournies par l'appelant.
- La méthode accepte un scope produit ou feature via `feature_id`, réutilise les champs déjà présents dans `ProductRunState` et dans `feature_states`, et n'interroge jamais Git.
- Le contrat impose un verrou déjà détenu par l'appelant : verrou produit pour les preuves produit, verrou feature pour les preuves d'une feature.
- Les mises à jour passent par `_run_logged_transition()` pour conserver la journalisation `INTENTION_START -> ACTION_APPLIED -> ACTION_COMPLETED`.
- Les mises à jour sont partielles : seuls les champs explicitement fournis sont modifiés, les autres restent inchangés dans `state.json`.
- La méthode est idempotente : si les preuves fournies correspondent déjà à l'état persistant, aucune nouvelle écriture ni journalisation métier n'est produite.
- Les valeurs ambiguës sont refusées : appel sans champ de preuve, champ non chaîne, ou chaîne vide/blanche.
- `ProductStateManager` exige désormais un verrou actif, localement détenu et revalidé sur disque avant toute écriture de `state.json`, `checkpoint.json` ou `journal.jsonl`.
- La validation de verrou contrôle `run_id`, `owner_logical`, `owner_pid`, `owner_host`, l'existence réelle du fichier verrou et l'absence d'expiration.
- Une exception d'amorçage bornée a été ajoutée pour la seule matérialisation initiale du namespace produit ; l'audit des acquisitions/libérations de verrou contourne la garde de journal uniquement pour éviter la dépendance circulaire.
- `ProductRuntime` encapsule désormais les mutations persistantes majeures dans un helper central `_run_logged_transition()`.
- Ce helper écrit une intention avant mutation, une entrée `action_applied` après mutation réussie, puis un résultat `action_completed`, ou un `action_failed` en cas d'exception.
- Les mutations `finish_run`, `update_feature_state`, `update_task_state`, `create_run_checkpoint`, `register_feature_graph_id`, `attach_child_artifacts`, `record_durable_decision` et `approve_durable_decision` passent maintenant par ce mécanisme central.
- Les opérations imbriquées réutilisent le verrou courant via `_managed_lock()` pour éviter les deadlocks et empêcher la création de faux positifs concurrentiels.
- `reconstruct_state()` verrouille la resynchronisation des décisions durables quand elle doit réécrire l'état reconstruit.
- Les garanties existantes ont été conservées : snapshot immuable, détection détaillée des divergences, unicité des graph IDs, artefacts legacy, récupération sûre des verrous expirés et décisions durables inter-runs.

## problèmes connus
- Aucun problème bloquant identifié dans le périmètre autorisé.
- La collecte effective des preuves depuis Git n'est volontairement pas traitée ici et reste dans le périmètre de T10.
- La réconciliation effective de ces preuves reste hors périmètre et sera traitée par T11.

## résultats des tests
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_state.py autodev/tests/test_product_runtime.py -q` : `145 passed in 0.38s`
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests -q` : `530 passed, 6 skipped in 11.65s`
- `git diff --check` : succès

## matrice des 18 critères et tests associés
- `AC-R2-1` : `test_creates_namespace_on_init`, `test_initialize_run_materializes_required_namespace_artifacts`
- `AC-R2-2` : `test_reconstructs_clean_state`, `test_reconstruction_is_clean_updated_after_git_checks`, `test_reconstruction_detects_checkpoint_incompatible`
- `AC-R2-3` : `test_reconstruction_detects_status_divergence`, `test_reconstruction_detects_base_commit_divergence`, `test_reconstruction_detects_integrated_commit_divergence`, `test_reconstruction_detects_dependency_divergence`, `test_reconstruction_detects_missing_required_child_artifact`, `test_reconstruction_detects_divergent_required_child_artifact`
- `AC-R2-4` : `test_reconstruction_does_not_trust_plan_status_or_narrative_report`
- `AC-R13-1` : `test_create_generates_unique_run_ids`, `test_initialize_run_materializes_required_namespace_artifacts`, `test_creates_entry_with_required_fields`
- `AC-R13-2` : `test_finish_run_journals_intention_action_and_result_in_order`, `test_finish_run_journals_intention_then_failure_on_error`, `test_records_idempotent_action_intention`, `test_completes_idempotent_action`
- `AC-R13-3` : `test_complete_idempotent_action_is_not_double_counted_on_resume`, `test_idempotence_prevents_double_completion`, `test_ensures_idempotence_prevents_duplication`
- `AC-R13-4` : `test_creates_key_from_components`, `test_converts_to_dict`, `test_creates_from_dict`
- `AC-R13-5` : `test_gets_checkpoints_path`, `test_creates_run_checkpoint`, `test_writes_and_reads_checkpoint`
- `AC-R13-6` : `test_product_graph_id_is_distinct`, `test_rejects_feature_graph_id_reused_by_product_graph`, `test_rejects_feature_graph_id_reused_across_runs`, `test_feature_graph_ids_are_distinct_and_tracked`, `test_reconstruction_detects_missing_product_graph_id`, `test_reconstruction_detects_feature_graph_ids_missing_on_complete`
- `AC-R13-7` : `test_attach_child_artifacts_persists_legacy_and_required_metadata`, `test_attach_child_artifacts_is_idempotent_and_journaled`
- `AC-R13-8` : `test_prevents_concurrent_product_lock`, `test_prevents_concurrent_feature_lock`, `test_rejects_concurrent_product_lock_acquisition`, `test_rejects_concurrent_feature_lock_acquisition`
- `AC-R13-9` : `test_creates_lock`, `test_converts_to_dict`, `test_acquires_product_lock`, `test_acquires_feature_lock`
- `AC-R13-10` : `test_rejects_state_write_without_lock_after_initialization`, `test_rejects_checkpoint_write_without_lock_after_initialization`, `test_rejects_journal_write_without_lock_after_initialization`, `test_allows_state_checkpoint_and_journal_writes_with_owned_lock`, `test_rejects_write_when_only_foreign_lock_exists`, `test_rejects_write_after_owned_lock_is_replaced`, `test_rejects_write_after_owned_lock_is_deleted`, `test_finish_run_reuses_existing_product_lock_without_deadlock`, `test_acquire_task_lock_prevents_concurrent_writes`
- `AC-R13-11` : `test_refuses_recovery_of_expired_lock_when_owner_process_is_still_alive`, `test_recovers_expired_lock_when_local_owner_is_confirmed_inactive`, `test_refuses_recovery_of_unverifiable_expired_lock`, `test_refuses_recovery_when_lock_changes_during_reclamation`
- `AC-R29-1` : `test_initializes_run`, `test_loads_approved_durable_decisions_across_runs_for_same_product`
- `AC-R29-2` : `test_records_durable_decision`, `test_approves_durable_decision`, `test_durable_decisions_persist_across_runtime_instances`, `test_durable_decisions_remain_available_without_run_a_namespace`
- `AC-R29-3` : `test_loads_approved_durable_decisions_across_runs_for_same_product`, `test_loading_durable_decisions_is_idempotent_across_reinitialization`, `test_reconstruct_state_reloads_approved_durable_decisions`, `test_apply_durable_decisions_to_backlog_detects_conflicts`, `test_apply_durable_decisions_to_backlog_scope_extension`

## prochaine étape
Brancher T10 sur `ProductRuntime.record_git_evidence()` pour alimenter les preuves structurées depuis Git, puis laisser T11 exploiter ces preuves pour la réconciliation.
