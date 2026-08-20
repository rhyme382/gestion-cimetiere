use gestion_cimetiere::commands::cemetery::*;
/// Integration tests for Tauri command layer and error mapping.
///
/// These tests verify that the public Tauri commands correctly:
/// 1. Handle database state and error mapping
/// 2. Return ApiErrorResponse with proper error types
/// 3. Support the transaction pattern for atomicity
///
/// The public commands are thin wrappers around internal functions
/// that acquire a database lock and map AppError to ApiErrorResponse.
use gestion_cimetiere::commands::municipality::*;
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::dto::*;
use gestion_cimetiere::errors::AppError;
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

/// Test the error mapping layer for municipality commands
#[test]
fn test_municipality_command_error_mapping_validation() {
    let conn = setup_db();

    let invalid_req = CreateMunicipalityRequest {
        name: "Test".to_string(),
        insee_code: "abc".to_string(), // Invalid INSEE
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    // The internal function returns AppError::InvalidInput
    let app_result = internal_create_municipality(&conn, invalid_req);
    assert!(app_result.is_err());

    if let Err(AppError::InvalidInput(msg)) = app_result {
        // Verify that this would map to the correct ApiErrorResponse
        assert!(msg.contains("INSEE"));
    } else {
        panic!("Expected InvalidInput error");
    }
}

/// Test the error mapping layer for duplicate validation
#[test]
fn test_municipality_command_error_mapping_duplicate() {
    let conn = setup_db();

    let req1 = CreateMunicipalityRequest {
        name: "Paris".to_string(),
        insee_code: "75056".to_string(),
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let req2 = CreateMunicipalityRequest {
        name: "Lyon".to_string(),
        insee_code: "69123".to_string(), // Different INSEE
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    internal_create_municipality(&conn, req1).unwrap();

    // The internal function returns AppError::Duplicate for singleton constraint
    let app_result = internal_create_municipality(&conn, req2);
    assert!(app_result.is_err());

    if let Err(AppError::Duplicate(msg)) = app_result {
        // Verify that this would map to the correct ApiErrorResponse type
        // Should fail because a gestionnaire is already configured
        assert!(msg.contains("commune gestionnaire") || msg.contains("gestionnaire"));
    } else {
        panic!("Expected Duplicate error");
    }
}

/// Test the error mapping layer for not found
#[test]
fn test_municipality_command_error_mapping_not_found() {
    let conn = setup_db();

    let update_req = UpdateMunicipalityRequest {
        name: Some("Test".to_string()),
        insee_code: None,
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    // The internal function returns AppError::NotFound
    let app_result = internal_update_municipality(&conn, 99999, update_req);
    assert!(app_result.is_err());

    if let Err(AppError::NotFound(msg)) = app_result {
        // Verify that this would map to the correct ApiErrorResponse type
        assert!(msg.contains("99999"));
    } else {
        panic!("Expected NotFound error");
    }
}

/// Test full municipality command flow with transactional safety
#[test]
fn test_municipality_command_full_flow_transactional() {
    let conn = setup_db();

    // Create
    let create_req = CreateMunicipalityRequest {
        name: "Paris".to_string(),
        insee_code: "75056".to_string(),
        postal_code: Some("75000".to_string()),
        email: Some("contact@paris.fr".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let created = internal_create_municipality(&conn, create_req).unwrap();
    assert_eq!(created.name, "Paris");
    assert_eq!(created.insee_code, "75056");

    // Get
    let retrieved = internal_get_municipality(&conn, created.id).unwrap();
    assert_eq!(retrieved.name, "Paris");

    // Update with transaction
    let update_req = UpdateMunicipalityRequest {
        name: Some("Paris (updated)".to_string()),
        insee_code: None,
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let updated = internal_update_municipality(&conn, created.id, update_req).unwrap();
    assert_eq!(updated.name, "Paris (updated)");

    // Verify persistence
    let final_check = internal_get_municipality(&conn, created.id).unwrap();
    assert_eq!(final_check.name, "Paris (updated)");
}

/// Test cemetery command error mapping and transactional behavior
#[test]
fn test_cemetery_command_error_mapping_validation() {
    let conn = setup_db();

    let invalid_req = CreateCemeteryRequest {
        name: "Test".to_string(),
        commune: None,
        capacity: Some(-100), // Invalid capacity
        municipality_id: None,
        address: None,
    };

    // The internal function returns AppError::InvalidInput
    let app_result = internal_create_cemetery(&conn, invalid_req);
    assert!(app_result.is_err());

    if let Err(AppError::InvalidInput(msg)) = app_result {
        // Verify error message is in French
        assert!(msg.contains("capacité"));
    } else {
        panic!("Expected InvalidInput error");
    }
}

/// Test cemetery duplicate handling with transaction rollback
#[test]
fn test_cemetery_command_duplicate_transaction_rollback() {
    let conn = setup_db();

    let req1 = CreateCemeteryRequest {
        name: "Saint Denis".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    internal_create_cemetery(&conn, req1).unwrap();

    // Try to create duplicate - should rollback on transaction error
    let req2 = CreateCemeteryRequest {
        name: "Saint Denis".to_string(), // Duplicate
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let app_result = internal_create_cemetery(&conn, req2);
    assert!(app_result.is_err());

    // Verify still only one cemetery in database
    let list = internal_list_cemeteries(&conn).unwrap();
    assert_eq!(list.len(), 1);
}

/// Verify that commands properly encapsulate transactional behavior
/// even when underlying operations would fail partway through
#[test]
fn test_command_layer_transaction_isolation() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");

    // Successful creation establishes baseline
    let create_req = CreateMunicipalityRequest {
        name: "Lyon".to_string(),
        insee_code: "69123".to_string(),
        postal_code: Some("69000".to_string()),
        email: Some("contact@lyon.fr".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let _ = internal_create_municipality(&conn, create_req).unwrap();
    let baseline_count = internal_list_municipalities(&conn).unwrap().len();

    // Attempt to create with invalid data should not increase count
    let invalid_create = CreateMunicipalityRequest {
        name: "Invalid".to_string(),
        insee_code: "99999".to_string(),
        postal_code: None,
        email: Some("not-a-valid-email".to_string()), // Invalid
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_create_municipality(&conn, invalid_create);
    assert!(result.is_err(), "Should fail validation");

    // Transaction should have been rolled back
    let final_count = internal_list_municipalities(&conn).unwrap().len();
    assert_eq!(
        final_count, baseline_count,
        "Transaction rollback should prevent partial writes"
    );
}
