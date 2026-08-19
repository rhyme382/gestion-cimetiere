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

#[test]
fn test_municipality_commands_create_success() {
    let conn = setup_db();

    let req = CreateMunicipalityRequest {
        name: "Lyon".to_string(),
        insee_code: "69123".to_string(),
        postal_code: Some("69000".to_string()),
        email: Some("contact@lyon.fr".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_create_municipality(&conn, req);
    assert!(result.is_ok());
    let created = result.unwrap();
    assert_eq!(created.name, "Lyon");
    assert_eq!(created.insee_code, "69123");
}

#[test]
fn test_municipality_commands_create_invalid_insee() {
    let conn = setup_db();

    let req = CreateMunicipalityRequest {
        name: "Test".to_string(),
        insee_code: "123".to_string(), // Too short
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_create_municipality(&conn, req);
    assert!(result.is_err());
    match result {
        Err(AppError::InvalidInput(msg)) => assert!(msg.contains("INSEE")),
        _ => panic!("Expected InvalidInput error"),
    }
}

#[test]
fn test_municipality_commands_create_invalid_email() {
    let conn = setup_db();

    let req = CreateMunicipalityRequest {
        name: "Test".to_string(),
        insee_code: "75056".to_string(),
        postal_code: None,
        email: Some("not-an-email".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_create_municipality(&conn, req);
    assert!(result.is_err());
    match result {
        Err(AppError::InvalidInput(msg)) => {
            assert!(
                msg.to_lowercase().contains("mail"),
                "Expected email validation error, got: {}",
                msg
            );
        }
        _ => panic!("Expected InvalidInput error for invalid email"),
    }
}

#[test]
fn test_municipality_commands_get_success() {
    let conn = setup_db();

    let req = CreateMunicipalityRequest {
        name: "Paris".to_string(),
        insee_code: "75056".to_string(),
        postal_code: Some("75001".to_string()),
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let created = internal_create_municipality(&conn, req).unwrap();
    let retrieved = internal_get_municipality(&conn, created.id);

    assert!(retrieved.is_ok());
    let retrieved = retrieved.unwrap();
    assert_eq!(retrieved.name, "Paris");
    assert_eq!(retrieved.insee_code, "75056");
}

#[test]
fn test_municipality_commands_get_not_found() {
    let conn = setup_db();

    let result = internal_get_municipality(&conn, 99999);
    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(msg)) => assert!(msg.contains("99999")),
        _ => panic!("Expected NotFound error"),
    }
}

#[test]
fn test_municipality_commands_list() {
    let conn = setup_db();

    let req = CreateMunicipalityRequest {
        name: "Paris".to_string(),
        insee_code: "75056".to_string(),
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    internal_create_municipality(&conn, req).unwrap();

    // List should return exactly one gestionnaire
    let list = internal_list_municipalities(&conn);
    assert!(list.is_ok());
    assert_eq!(list.unwrap().len(), 1);
}

#[test]
fn test_municipality_commands_update_success() {
    let conn = setup_db();

    let req = CreateMunicipalityRequest {
        name: "Original".to_string(),
        insee_code: "12345".to_string(),
        postal_code: Some("12000".to_string()),
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let created = internal_create_municipality(&conn, req).unwrap();

    let update_req = UpdateMunicipalityRequest {
        name: Some("Updated".to_string()),
        insee_code: None,
        postal_code: Some("12001".to_string()),
        email: Some("contact@example.com".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_update_municipality(&conn, created.id, update_req);
    assert!(result.is_ok());
    let updated = result.unwrap();
    assert_eq!(updated.name, "Updated");
    assert_eq!(updated.postal_code, Some("12001".to_string()));
}

#[test]
fn test_municipality_commands_update_not_found() {
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

    let result = internal_update_municipality(&conn, 99999, update_req);
    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(_)) => {}
        _ => panic!("Expected NotFound error"),
    }
}

#[test]
fn test_municipality_commands_delete_success() {
    let conn = setup_db();

    let req = CreateMunicipalityRequest {
        name: "ToDelete".to_string(),
        insee_code: "99999".to_string(),
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let created = internal_create_municipality(&conn, req).unwrap();
    let result = internal_delete_municipality(&conn, created.id);

    // Deletion of gestionnaire should fail
    assert!(result.is_err());
    match result {
        Err(AppError::Internal(msg)) => {
            assert!(msg.contains("commune gestionnaire"));
        }
        _ => panic!("Expected Internal error for deleting gestionnaire"),
    }

    // Verify it still exists
    let get_result = internal_get_municipality(&conn, created.id);
    assert!(get_result.is_ok());
}

#[test]
fn test_municipality_commands_delete_not_found() {
    let conn = setup_db();

    let result = internal_delete_municipality(&conn, 99999);
    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(msg)) => {
            assert!(msg.contains("99999"));
        }
        _ => panic!("Expected NotFound error when deleting non-existent municipality"),
    }
}

#[test]
fn test_municipality_commands_transaction_rollback_on_duplicate_insee() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");

    let req1 = CreateMunicipalityRequest {
        name: "First".to_string(),
        insee_code: "12345".to_string(),
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    internal_create_municipality(&conn, req1).unwrap();

    // Try to create a second gestionnaire
    let req2 = CreateMunicipalityRequest {
        name: "Second".to_string(),
        insee_code: "54321".to_string(), // Different INSEE
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_create_municipality(&conn, req2);
    assert!(result.is_err());
    match result {
        Err(AppError::Duplicate(_)) => {}
        _ => panic!("Expected Duplicate error"),
    }

    // Verify only first municipality exists
    let list = internal_list_municipalities(&conn).unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].name, "First");
}

#[test]
fn test_municipality_create_transaction_atomicity() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");

    // Create first municipality successfully
    let req1 = CreateMunicipalityRequest {
        name: "Valid".to_string(),
        insee_code: "99999".to_string(),
        postal_code: Some("99000".to_string()),
        email: Some("valid@example.com".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let result1 = internal_create_municipality(&conn, req1);
    assert!(result1.is_ok());
    let count_after_success = internal_list_municipalities(&conn).unwrap().len();
    assert_eq!(count_after_success, 1);

    // Try to create with invalid email (should rollback entire transaction)
    let req2 = CreateMunicipalityRequest {
        name: "Invalid".to_string(),
        insee_code: "88888".to_string(),
        postal_code: None,
        email: Some("invalid-email".to_string()), // Invalid email
        department: None,
        region: None,
        notes: None,
    };

    let result2 = internal_create_municipality(&conn, req2);
    assert!(result2.is_err());

    // Verify that count hasn't increased due to transaction rollback
    let count_after_error = internal_list_municipalities(&conn).unwrap().len();
    assert_eq!(
        count_after_error, 1,
        "Transaction should have rolled back on validation error"
    );
}

#[test]
fn test_municipality_update_transaction_atomicity() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");

    let req = CreateMunicipalityRequest {
        name: "Original".to_string(),
        insee_code: "11111".to_string(),
        postal_code: Some("11000".to_string()),
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let created = internal_create_municipality(&conn, req).unwrap();
    let id = created.id;

    // Try to update with invalid INSEE (should rollback)
    let invalid_update = UpdateMunicipalityRequest {
        name: Some("Updated".to_string()),
        insee_code: Some("abc".to_string()), // Invalid INSEE
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_update_municipality(&conn, id, invalid_update);
    assert!(result.is_err());

    // Verify original data hasn't changed
    let retrieved = internal_get_municipality(&conn, id).unwrap();
    assert_eq!(retrieved.name, "Original");
    assert_eq!(retrieved.insee_code, "11111");
}

#[test]
fn test_municipality_commands_validation_differentiation() {
    let conn = setup_db();

    // Test validation error
    let invalid_req = CreateMunicipalityRequest {
        name: "Test".to_string(),
        insee_code: "abc".to_string(), // Invalid
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_create_municipality(&conn, invalid_req);
    assert!(result.is_err());
    match result {
        Err(AppError::InvalidInput(_)) => {}
        _ => panic!("Expected InvalidInput error"),
    }

    // Test not found error
    let update_req = UpdateMunicipalityRequest {
        name: Some("Test".to_string()),
        insee_code: None,
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let result = internal_update_municipality(&conn, 99999, update_req);
    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(_)) => {}
        _ => panic!("Expected NotFound error"),
    }
}
