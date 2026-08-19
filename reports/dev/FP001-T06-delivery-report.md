# Rapport de livraison — FP001-T06

## Résultat

- Tâche : `FP001-T06`
- Statut fonctionnel : validations réussies
- Périmètre : conforme

## Fichiers modifiés

- `tests/e2e/11-commune-cemeteries.spec.ts`
- `reports/dev/FP001-T06-delivery-report.md`

## Preuve E2E

Le test Playwright unique `full E2E scenario: configure commune, create two cemeteries, modify one, and verify persistence` couvre successivement :

1. la modification et l’enregistrement de la commune ;
2. la création de deux cimetières ;
3. la modification de l’un des cimetières ;
4. la navigation hors de la vue puis le retour ;
5. la persistance de la commune et des deux cimetières ;
6. la persistance de la modification du cimetière.

## Sorties exactes des validations

Les blocs suivants sont générés mécaniquement depuis `.autodev/runs/FP001-T06/review/validation-results.json`, sans reformulation.

### Validation 1

Commande : `cargo test -p gestion-cimetiere`

Code de sortie : `0`

Expiration : `False`

#### stdout

```text

running 132 tests
test commands::alert::tests::test_list_alerts_signature ... ok
test commands::alert::tests::test_get_alert_summary_signature ... ok
test commands::alert::tests::test_acknowledge_alert_signature ... ok
test commands::alert::tests::test_refresh_alerts_signature ... ok
test commands::backup::tests::test_backup_commands_signature ... ok
test commands::diagnostic::tests::test_build_diagnostic_result_when_sqlite_succeeds ... ok
test commands::diagnostic::tests::test_diagnostic_dto_healthy ... ok
test commands::diagnostic::tests::test_build_diagnostic_result_when_sqlite_fails ... ok
test commands::diagnostic::tests::test_diagnostic_dto_sqlite_error ... ok
test commands::diagnostic::tests::test_diagnostic_returns_app_version ... ok
test commands::diagnostic::tests::test_diagnostic_sqlite_error_message_structure ... ok
test commands::pdf::tests::test_generate_concession_pdf_signature ... ok
test core::models::concession::tests::calculate_expires_at_uses_civil_date_format ... ok
test core::models::concession::tests::calculate_expires_at_adjusts_leap_day ... ok
test core::models::concession::tests::calculate_status_reports_active_soon_expiring_and_expired ... ok
test core::models::concession::tests::validate_accepts_iso_civil_date ... ok
test core::models::concession::tests::prepare_for_storage_calculates_expiry_and_status ... ok
test commands::diagnostic::tests::test_diagnostic_healthy_with_in_memory_db ... ok
test core::models::concession::tests::validate_rejects_french_date_format ... ok
test core::models::concession::tests::validate_rejects_rfc3339_timestamp ... ok
test commands::diagnostic::tests::test_diagnostic_with_temp_file_db ... ok
test commands::diagnostic::tests::test_diagnostic_sqlite_error_behavior ... ok
test db::connection::tests::test_foreign_keys_enabled ... ok
test db::connection::tests::test_init_db_in_memory ... ok
test db::migrations::tests::migration_with_backfill_scenario ... ok
test db::migrations::tests::test_migration_0009_preserves_existing_cemetery_data ... ok
test db::migrations::tests::integration_cemetery ... ok
test db::migrations::tests::test_migration_0009_backfills_municipality_id_from_commune ... ok
test db::migrations::tests::test_migration_0010_backfill_municipalities_for_fp001_r2_ac5 ... ok
test db::migrations::tests::test_migration_0008_creates_municipalities_table ... ok
test db::migrations::tests::test_migration_0008_municipality_name_uniqueness ... ok
test db::migrations::tests::test_migrations ... ok
test db::migrations::tests::test_concession_number_uniqueness_normalized ... ok
test db::migrations::tests::test_migration_0009_extends_cemeteries_table ... ok
test db::migrations::tests::test_migration_0007_adds_required_columns ... ok
test db::migrations::tests::test_migration_0008_0009_idempotent ... ok
test db::migrations::tests::test_concession_number_null_multiple_allowed ... ok
test db::migrations::tests::test_migrations_are_idempotent ... ok
test db::migrations::tests::test_concession_number_empty_string_rejected ... ok
test db::repositories::alert_repo::tests::test_acknowledge_alert ... ok
test db::migrations::tests::test_migration_from_pre_0007_database ... ok
test db::repositories::alert_repo::tests::test_create_alert ... ok
test db::repositories::alert_repo::tests::test_get_alert_summary ... ok
test db::repositories::alert_repo::tests::test_get_alerts_by_concession ... ok
test db::repositories::alert_repo::tests::test_list_unacknowledged_alerts ... ok
test db::repositories::alert_repo::tests::test_list_alerts ... ok
test db::repositories::concession_repo::tests::test_cinquantenaire_validation_requires_50_years ... ok
test db::repositories::concession_repo::tests::test_cinquantenaire_validation_requires_start_date ... ok
test db::migrations::tests::test_migrations_run_on_empty_db ... ok
test db::migrations::tests::test_no_data_loss_during_migration ... ok
test db::repositories::burial_repo::tests::test_fk_constraint_concession ... ok
test db::repositories::burial_repo::tests::test_fk_constraint_individual ... ok
test db::repositories::concession_repo::tests::test_expires_at_calculation_leap_year_edge_case ... ok
test db::repositories::concession_repo::tests::test_expires_at_calculation_leap_year_feb29 ... ok
test db::repositories::concession_repo::tests::test_expires_at_calculation_perpetuelle ... ok
test db::repositories::concession_repo::tests::test_expires_at_calculation_temporaire ... ok
test db::repositories::burial_repo::tests::test_get_non_existent_burial ... ok
test db::repositories::cemetery_repo::tests::test_cemetery_name_normalization_case ... ok
test db::repositories::burial_repo::tests::test_create_and_get_burial ... ok
test db::repositories::cemetery_repo::tests::test_cemetery_inactive_not_checked_for_uniqueness ... ok
test db::repositories::burial_repo::tests::test_list_by_concession ... ok
test db::repositories::concession_repo::tests::test_perpetuelle_validation_no_duration ... ok
test db::repositories::concession_repo::tests::test_perpetuelle_validation_requires_start_date ... ok
test db::repositories::cemetery_repo::tests::test_create_and_get_cemetery ... ok
test db::repositories::cemetery_repo::tests::test_cemetery_name_normalization_spaces ... ok
test db::repositories::cemetery_repo::tests::test_delete_cemetery ... ok
test db::repositories::cemetery_repo::tests::test_get_non_existent_cemetery ... ok
test db::repositories::cemetery_repo::tests::test_list_cemeteries ... ok
test db::repositories::concession_repo::tests::test_status_calculation_with_reference_date ... ok
test db::repositories::concession_repo::tests::test_status_echeance_proche_12_months_boundary ... ok
test db::repositories::concession_repo::tests::test_temporaire_validation_duration_range ... ok
test db::repositories::concession_repo::tests::test_temporaire_validation_requires_duration ... ok
test db::repositories::concession_repo::tests::test_temporaire_validation_requires_start_date ... ok
test db::repositories::concession_repo::tests::test_trentenaire_validation_requires_30_years ... ok
test db::repositories::concession_repo::tests::test_trentenaire_validation_requires_start_date ... ok
test db::repositories::concession_repo::tests::test_concession_with_holder_data ... ok
test db::repositories::cemetery_repo::tests::test_update_cemetery ... ok
test db::repositories::concession_repo::tests::test_create_and_get_concession ... ok
test db::repositories::concession_repo::tests::test_create_with_nonexistent_cemetery ... ok
test db::repositories::concession_repo::tests::test_fk_constraint_cemetery ... ok
test db::repositories::concession_repo::tests::test_create_with_nonexistent_plot ... ok
test db::repositories::concession_repo::tests::test_get_at_with_reference_date_active ... ok
test db::repositories::concession_repo::tests::test_get_non_existent_concession ... ok
test db::repositories::concession_repo::tests::test_plot_occupation_at_with_reference_date ... ok
test db::repositories::concession_repo::tests::test_list_at_with_reference_date ... ok
test db::repositories::concession_repo::tests::test_list_concessions ... ok
test db::repositories::concession_repo::tests::test_plot_occupation_expired_concession_allows_new ... ok
test db::repositories::concession_repo::tests::test_plot_occupation_validation ... ok
test db::repositories::concession_repo::tests::test_status_calculation_perpetuelle ... ok
test db::repositories::concession_repo::tests::test_update_non_existent_concession ... ok
test db::repositories::concession_repo::tests::test_update_concession ... ok
test db::repositories::concession_repo::tests::test_update_reactivate_concession_on_same_plot_with_active_conflict ... ok
test db::repositories::concession_repo::tests::test_update_extend_concession_on_same_plot_with_active_conflict ... ok
test db::repositories::individual_repo::tests::test_create_and_get_individual ... ok
test db::repositories::individual_repo::tests::test_get_non_existent_individual ... ok
test db::repositories::individual_repo::tests::test_list_individuals ... ok
test db::repositories::individual_repo::tests::test_search_individual ... ok
test db::repositories::individual_repo::tests::test_update_individual ... ok
test db::repositories::municipality_repo::tests::test_duplicate_name ... ok
test db::repositories::individual_repo::tests::test_update_non_existent_individual ... ok
test db::repositories::municipality_repo::tests::test_create_municipality_success ... ok
test db::repositories::municipality_repo::tests::test_compatibility_placeholder_00000_not_counted_as_gestionnaire ... ok
test db::repositories::municipality_repo::tests::test_duplicate_insee_code ... ok
test db::repositories::municipality_repo::tests::test_email_validation ... ok
test dto::alert::tests::test_alert_dto_creation ... ok
test dto::alert::tests::test_alert_summary_aggregation ... ok
test dto::alert::tests::test_alert_type_as_str ... ok
test dto::alert::tests::test_alert_type_from_str ... ok
test dto::alert::tests::test_alert_type_serialization ... ok
test dto::concession::update_request_tests::update_request_distinguishes_absent_null_and_value ... ok
test db::repositories::municipality_repo::tests::test_get_by_id_bypasses_gestionnaire_filter ... ok
test db::repositories::municipality_repo::tests::test_get_municipality_not_found ... ok
test db::repositories::municipality_repo::tests::test_insee_code_validation_alphanumeric ... ok
test services::alert_service::tests::test_get_thresholds ... ok
test services::backup_service::tests::test_backup_filename_format ... ok
test services::backup_service::tests::test_validate_sqlite_header ... ok
test services::pdf_service::tests::test_pdf_header_marker ... ok
test services::pdf_service::tests::test_pdf_filename_format ... ok
test db::repositories::municipality_repo::tests::test_insee_code_validation_length ... ok
test db::repositories::municipality_repo::tests::test_insee_code_uppercase_normalization ... ok
test services::alert_service::tests::test_calculate_alerts_no_concessions ... ok
test services::alert_service::tests::test_calculate_alerts_no_expiry_dates ... ok
test db::repositories::municipality_repo::tests::test_list_empty_when_no_gestionnaire ... ok
test db::repositories::municipality_repo::tests::test_municipality_persistence ... ok
test db::repositories::municipality_repo::tests::test_update_municipality ... ok
test db::repositories::plot_repo::tests::test_create_and_get_plot ... ok
test db::repositories::municipality_repo::tests::test_list_municipalities ... ok
test db::repositories::municipality_repo::tests::test_singleton_gestionnaire_cannot_be_deleted ... ok
test db::repositories::plot_repo::tests::test_get_non_existent_plot ... ok
test db::repositories::plot_repo::tests::test_update_non_existent_plot ... ok
test db::repositories::plot_repo::tests::test_update_plot ... ok
test db::repositories::plot_repo::tests::test_list_plots ... ok

test result: ok. 132 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.36s


running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


running 4 tests
test test_integration_alert_creation_and_retrieval ... ok
test test_integration_alert_acknowledgment ... ok
test test_integration_alert_foreign_key_cascade ... ok
test test_integration_alert_types_trigger_correctly ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


running 8 tests
test test_backup_nonexistent_db ... ok
test test_list_backups_empty ... ok
test test_path_traversal_prevention ... ok
test test_backup_creation ... ok
test test_restore_invalid_backup ... ok
test test_list_backups_multiple ... ok
test test_restore_invalid_sqlite_file ... ok
test test_restore_backup ... ok

test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


running 4 tests
test test_burial_get_by_id ... ok
test test_burial_create_and_list ... ok
test test_burial_multiple_individuals_same_concession ... ok
test test_full_burial_workflow ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s


running 6 tests
test integration_cemetery_migration_with_backfill ... ok
test test_cemetery_delete ... ok
test test_cemetery_create_and_list ... ok
test test_cemetery_update ... ok
test integration_cemetery_preserves_legacy_data ... ok
test test_full_cemetery_workflow ... ok

test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s


running 17 tests
test test_cemetery_commands_validation_differentiation ... ok
test test_cemetery_commands_create_duplicate_name ... ok
test test_cemetery_commands_update_not_found ... ok
test test_cemetery_commands_create_invalid_capacity ... ok
test test_cemetery_commands_case_insensitive_uniqueness ... ok
test test_cemetery_commands_create_normalization ... ok
test test_cemetery_commands_get_not_found ... ok
test test_cemetery_commands_get_success ... ok
test test_cemetery_commands_transaction_rollback_on_duplicate ... ok
test test_cemetery_commands_soft_delete_reusable_name ... ok
test test_cemetery_commands_delete_not_found ... ok
test test_cemetery_commands_create_success ... ok
test test_cemetery_commands_update_success ... ok
test test_cemetery_commands_delete_soft_delete ... ok
test test_cemetery_commands_list ... ok
test test_cemetery_create_transaction_atomicity ... ok
test test_cemetery_update_transaction_atomicity ... ok

test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.09s


running 27 tests
test test_concession_number_is_required ... ok
test test_concession_acquired_date_tracking ... ok
test test_concession_status_perpetuelle_never_expires ... ok
test test_concession_validation_cinquantenaire_enforces_duration ... ok
test test_concession_validation_temporal_with_invalid_duration ... ok
test test_concession_validation_trentenaire_enforces_duration ... ok
test test_concession_renewable_status_tracking ... ok
test test_concession_holder_persistence ... ok
test test_concession_50year_lifecycle ... ok
test test_concession_30year_lifecycle ... ok
test test_concession_expiry_boundary_1_day_window ... ok
test test_concession_leap_year_expiry_feb29_to_leap ... ok
test test_concession_short_term_lifecycle ... ok
test test_concession_status_transition_active_to_soon_expiring ... ok
test test_concession_number_must_be_unique ... ok
test test_concession_number_assignment ... ok
test test_concession_update ... ok
test test_concession_create_and_list ... ok
test test_concession_leap_year_expiry_feb29_to_non_leap ... ok
test test_concession_list_all ... ok
test test_concession_update_with_status_recalculation ... ok
test test_concession_with_observations ... ok
test test_multiple_concessions_different_statuses_at_same_reference_date ... ok
test test_full_concession_workflow ... ok
test test_plot_occupation_prevents_duplicate_active_concessions ... ok
test test_concession_with_plot ... ok
test test_plot_occupation_allows_expired_concessions_to_be_replaced ... ok

test result: ok. 27 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.11s


running 5 tests
test test_individual_create_and_list ... ok
test test_individual_with_optional_fields ... ok
test test_full_individual_workflow ... ok
test test_individual_update ... ok
test test_individual_search ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s


running 8 tests
test test_municipality_update_with_rollback ... ok
test test_municipality_create_with_lowercase_insee ... ok
test test_full_municipality_workflow ... ok
test test_municipality_transaction_rollback_on_duplicate_insee ... ok
test test_municipality_duplicate_normalized_insee ... ok
test test_municipality_persistence_after_reopen ... ok
test test_municipality_validation_errors_differentiation ... ok
test test_municipality_email_validation_in_update ... ok

test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s


running 14 tests
test test_municipality_commands_get_not_found ... ok
test test_municipality_commands_create_invalid_insee ... ok
test test_municipality_commands_get_success ... ok
test test_municipality_commands_create_success ... ok
test test_municipality_commands_delete_not_found ... ok
test test_municipality_commands_validation_differentiation ... ok
test test_municipality_commands_update_success ... ok
test test_municipality_commands_create_invalid_email ... ok
test test_municipality_commands_list ... ok
test test_municipality_commands_update_not_found ... ok
test test_municipality_commands_delete_success ... ok
test test_municipality_commands_transaction_rollback_on_duplicate_insee ... ok
test test_municipality_update_transaction_atomicity ... ok
test test_municipality_create_transaction_atomicity ... ok

test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.07s


running 3 tests
test test_integration_pdf_generation_basic ... ok
test test_integration_pdf_with_multiple_burials ... ok
test test_integration_pdf_with_burials ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s


running 4 tests
test test_plot_empty_list_for_cemetery ... ok
test test_plot_create_and_list ... ok
test test_plot_update ... ok
test test_full_plot_workflow ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s


running 7 tests
test test_command_layer_transaction_isolation ... ok
test test_cemetery_command_duplicate_transaction_rollback ... ok
test test_cemetery_command_error_mapping_validation ... ok
test test_municipality_command_error_mapping_duplicate ... ok
test test_municipality_command_error_mapping_validation ... ok
test test_municipality_command_error_mapping_not_found ... ok
test test_municipality_command_full_flow_transactional ... ok

test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s


running 13 tests
test test_tauri_command_get_municipality_not_found ... ok
test test_tauri_command_create_municipality_success ... ok
test test_tauri_command_create_cemetery_duplicate_name ... ok
test test_tauri_command_create_cemetery_success ... ok
test test_tauri_command_response_serialization ... ok
test test_tauri_command_create_municipality_validation_error ... ok
test test_tauri_command_transaction_rollback ... ok
test test_tauri_command_delete_cemetery_success ... ok
test test_tauri_command_get_municipality_success ... ok
test test_tauri_command_get_cemetery_not_found ... ok
test test_tauri_command_get_cemetery_success ... ok
test test_tauri_command_create_cemetery_invalid_capacity ... ok
test test_tauri_command_municipality_error_serialization ... ok

test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.06s


running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

#### stderr

```text
   Compiling gestion-cimetiere v0.1.0 (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src-tauri)
warning: unused import: `super::*`
  --> src-tauri/src/commands/alert.rs:35:9
   |
35 |     use super::*;
   |         ^^^^^^^^
   |
   = note: `#[warn(unused_imports)]` (part of `#[warn(unused)]`) on by default

warning: unused import: `super::*`
  --> src-tauri/src/commands/backup.rs:36:9
   |
36 |     use super::*;
   |         ^^^^^^^^

warning: unused import: `super::*`
  --> src-tauri/src/commands/pdf.rs:56:9
   |
56 |     use super::*;
   |         ^^^^^^^^

warning: `gestion-cimetiere` (lib test) generated 3 warnings (run `cargo fix --lib -p gestion-cimetiere --tests` to apply 3 suggestions)
    Finished `test` profile [unoptimized + debuginfo] target(s) in 3.70s
     Running unittests src/lib.rs (target/debug/deps/gestion_cimetiere-a6ec06a652d9f270)
     Running unittests src/main.rs (target/debug/deps/gestion_cimetiere-73740e101ffc13bd)
     Running tests/integration_alert.rs (target/debug/deps/integration_alert-1106140cb0902f72)
     Running tests/integration_backup.rs (target/debug/deps/integration_backup-67f1d1b8f1912cc7)
     Running tests/integration_burial.rs (target/debug/deps/integration_burial-6de05c92dd9d1087)
     Running tests/integration_cemetery.rs (target/debug/deps/integration_cemetery-5c5e9565e773d4e7)
     Running tests/integration_cemetery_commands.rs (target/debug/deps/integration_cemetery_commands-00735da03a202c89)
     Running tests/integration_concession.rs (target/debug/deps/integration_concession-b324e8adf15ccd72)
     Running tests/integration_individual.rs (target/debug/deps/integration_individual-f99280441012492c)
     Running tests/integration_municipality.rs (target/debug/deps/integration_municipality-954d48e552afd140)
     Running tests/integration_municipality_commands.rs (target/debug/deps/integration_municipality_commands-e36169b194ff01d7)
     Running tests/integration_pdf.rs (target/debug/deps/integration_pdf-5cebb8161064afb7)
     Running tests/integration_plot.rs (target/debug/deps/integration_plot-80bc0a6cc53c38d8)
     Running tests/integration_tauri_commands.rs (target/debug/deps/integration_tauri_commands-4ccd827015039970)
     Running tests/integration_tauri_public_commands.rs (target/debug/deps/integration_tauri_public_commands-e149737a7b3bef0b)
   Doc-tests gestion_cimetiere
```

### Validation 2

Commande : `npm run test`

Code de sortie : `0`

Expiration : `False`

#### stdout

```text

> gestion-cimetiere@0.1.0 test
> vitest run


[1m[30m[46m RUN [49m[39m[22m [36mv4.1.9 [39m[90m/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06[39m

 [32m✓[39m src/__tests__/bindings.test.ts [2m([22m[2m25 tests[22m[2m)[22m[32m 20[2mms[22m[39m
 [32m✓[39m src/__tests__/tauri.test.ts [2m([22m[2m25 tests[22m[2m)[22m[32m 29[2mms[22m[39m
 [32m✓[39m src/__tests__/Sidebar.test.tsx [2m([22m[2m2 tests[22m[2m)[22m[32m 92[2mms[22m[39m
 [32m✓[39m src/__tests__/AppLayout.test.tsx [2m([22m[2m2 tests[22m[2m)[22m[32m 108[2mms[22m[39m
 [32m✓[39m src/__tests__/hooks/useQuery.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 236[2mms[22m[39m
 [32m✓[39m src/__tests__/DiagnosticCard.test.tsx [2m([22m[2m6 tests[22m[2m)[22m[32m 202[2mms[22m[39m
 [32m✓[39m src/__tests__/hooks/useMunicipalities.test.ts [2m([22m[2m16 tests[22m[2m)[22m[33m 350[2mms[22m[39m
 [32m✓[39m src/__tests__/CemeteryMap.test.tsx [2m([22m[2m12 tests[22m[2m)[22m[33m 405[2mms[22m[39m
 [32m✓[39m src/__tests__/concession-detail.test.tsx [2m([22m[2m17 tests[22m[2m)[22m[33m 559[2mms[22m[39m
 [32m✓[39m src/__tests__/cemetery-form.test.tsx [2m([22m[2m13 tests[22m[2m)[22m[33m 796[2mms[22m[39m
 [32m✓[39m src/__tests__/cemeteries-page.test.tsx [2m([22m[2m14 tests[22m[2m)[22m[33m 886[2mms[22m[39m
 [32m✓[39m src/__tests__/commune-settings.test.tsx [2m([22m[2m19 tests[22m[2m)[22m[33m 1012[2mms[22m[39m
     [33m[2m✓[22m[39m accepte la soumission avec les champs obligatoires remplis [33m 345[2mms[22m[39m
 [32m✓[39m src/__tests__/concessions-list.test.tsx [2m([22m[2m21 tests[22m[2m)[22m[33m 1111[2mms[22m[39m
 [32m✓[39m src/__tests__/concession-form.test.tsx [2m([22m[2m24 tests[22m[2m)[22m[33m 2717[2mms[22m[39m
     [33m[2m✓[22m[39m submits form with valid data [33m 396[2mms[22m[39m

[2m Test Files [22m [1m[32m14 passed[39m[22m[90m (14)[39m
[2m      Tests [22m [1m[32m201 passed[39m[22m[90m (201)[39m
[2m   Start at [22m 09:37:11
[2m   Duration [22m 4.63s[2m (transform 2.41s, setup 1.21s, import 6.36s, tests 8.52s, environment 14.71s)[22m
```

#### stderr

```text
09:37:11 [vite] warning: `esbuild` option was specified by "vite:react-babel" plugin. This option is deprecated, please use `oxc` instead.
09:37:11 [vite] warning: `optimizeDeps.esbuildOptions` option was specified by "vite:react-babel" plugin. This option is deprecated, please use `optimizeDeps.rolldownOptions` instead.
Both esbuild and oxc options were set. oxc options will be used and esbuild options will be ignored. The following esbuild options were set: `{ jsx: 'automatic', jsxImportSource: undefined }`
[90mstderr[2m | src/__tests__/commune-settings.test.tsx[2m > [22m[2mCommune Settings - ParametresPage[2m > [22m[2maffiche le titre et la description
[22m[39mWarning: An update to DiagnosticCard inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at DiagnosticCard (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/components/DiagnosticCard.tsx:20:72)
    at div
    at ParametresPage (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/pages/ParametresPage.tsx:18:128)
    at RenderedRoute (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6173:26)
    at Routes (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:7052:3)
    at Router (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6991:13)
    at MemoryRouter (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6907:3)
    at TestWrapper
Warning: An update to DiagnosticCard inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at DiagnosticCard (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/components/DiagnosticCard.tsx:20:72)
    at div
    at ParametresPage (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/pages/ParametresPage.tsx:18:128)
    at RenderedRoute (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6173:26)
    at Routes (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:7052:3)
    at Router (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6991:13)
    at MemoryRouter (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6907:3)
    at TestWrapper
Warning: An update to ParametresPage inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at ParametresPage (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/pages/ParametresPage.tsx:18:128)
    at RenderedRoute (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6173:26)
    at Routes (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:7052:3)
    at Router (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6991:13)
    at MemoryRouter (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6907:3)
    at TestWrapper
Warning: An update to ParametresPage inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at ParametresPage (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/pages/ParametresPage.tsx:18:128)
    at RenderedRoute (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6173:26)
    at Routes (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:7052:3)
    at Router (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6991:13)
    at MemoryRouter (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6907:3)
    at TestWrapper

[90mstderr[2m | src/__tests__/hooks/useMunicipalities.test.ts[2m > [22m[2mMunicipality hooks[2m > [22m[2museMunicipalities[2m > [22m[2mshould refetch municipalities
[22m[39mWarning: An update to TestComponent inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at TestComponent (/home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/@testing-library/react/dist/pure.js:328:5)
Warning: An update to TestComponent inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at TestComponent (/home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/@testing-library/react/dist/pure.js:328:5)

[90mstderr[2m | src/__tests__/hooks/useMunicipalities.test.ts[2m > [22m[2mMunicipality hooks[2m > [22m[2museMunicipalities[2m > [22m[2mshould refetch municipalities
[22m[39mWarning: An update to TestComponent inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at TestComponent (/home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/@testing-library/react/dist/pure.js:328:5)
Warning: An update to TestComponent inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at TestComponent (/home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/@testing-library/react/dist/pure.js:328:5)

[90mstderr[2m | src/__tests__/cemeteries-page.test.tsx[2m > [22m[2mCemeteriesPage[2m > [22m[2maffiche le titre et la description
[22m[39mWarning: An update to CemeteriesPage inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at CemeteriesPage (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/pages/CemeteriesPage.tsx:19:95)
    at Router (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6991:13)
    at BrowserRouter (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:10318:3)
    at TestWrapper (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/__tests__/cemeteries-page.test.tsx:52:24)
Warning: An update to CemeteriesPage inside a test was not wrapped in act(...).

When testing, code that causes React state updates should be wrapped into act(...):

act(() => {
  /* fire events that update state */
});
/* assert on the output */

This ensures that you're testing the behavior the user would see in the browser. Learn more at https://reactjs.org/link/wrap-tests-with-act
    at CemeteriesPage (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/pages/CemeteriesPage.tsx:19:95)
    at Router (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:6991:13)
    at BrowserRouter (file:///home/yaoshifo/Documents/dev/gestion-cimetiere/node_modules/react-router/dist/development/chunk-6CSD65Y2.mjs:10318:3)
    at TestWrapper (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/__tests__/cemeteries-page.test.tsx:52:24)

[90mstderr[2m | src/__tests__/CemeteryMap.test.tsx[2m > [22m[2mCemeteryMap Component[2m > [22m[2mshould handle empty sections gracefully
[22m[39mWarning: Received NaN for the `width` attribute. If this is expected, cast the value to a string.
    at svg
    at div
    at div
    at CemeteryMap (/home/yaoshifo/Documents/dev/gestion-cimetiere/.autodev/worktrees/FP001-T06/src/components/map/CemeteryMap.tsx:15:24)
```

### Validation 3

Commande : `npm run test:e2e -- tests/e2e/11-commune-cemeteries.spec.ts --project=chromium`

Code de sortie : `0`

Expiration : `False`

#### stdout

```text

> gestion-cimetiere@0.1.0 test:e2e
> playwright test tests/e2e/11-commune-cemeteries.spec.ts --project=chromium


Running 11 tests using 8 workers

[1/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:249:3 › Scenario 11: Configuration commune et gestion des cimetières › parametres page loads and displays municipality configuration form
[2/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:470:3 › Scenario 11: Configuration commune et gestion des cimetières › municipality configuration form fields can be updated
[3/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:273:3 › Scenario 11: Configuration commune et gestion des cimetières › full E2E scenario: configure commune, create two cemeteries, modify one, and verify persistence
[4/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:536:3 › Scenario 11: Configuration commune et gestion des cimetières › municipality data persists across form field interactions
[5/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:512:3 › Scenario 11: Configuration commune et gestion des cimetières › parametres page does not display loading spinners when data is loaded
[6/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:572:3 › Scenario 11: Configuration commune et gestion des cimetières › parametres page renders without JavaScript errors
[7/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:597:3 › Scenario 11: Configuration commune et gestion des cimetières › municipality configuration shows all expected form sections
[8/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:526:3 › Scenario 11: Configuration commune et gestion des cimetières › diagnostic card is visible on parametres page
[9/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:629:3 › Scenario 11: Configuration commune et gestion des cimetières › cemeteries page loads successfully
[10/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:645:3 › Scenario 11: Configuration commune et gestion des cimetières › create and manage cemeteries with mock backend
[11/11] [chromium] › tests/e2e/11-commune-cemeteries.spec.ts:708:3 › Scenario 11: Configuration commune et gestion des cimetières › cemetery persistence across navigation
  11 passed (14.9s)

To open last HTML report run:
[36m[39m
[36m  npx playwright show-report[39m
[36m[39m
```

#### stderr

```text

```
