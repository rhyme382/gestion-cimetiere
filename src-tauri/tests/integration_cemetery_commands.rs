use gestion_cimetiere::commands::cemetery::*;
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
fn test_cemetery_commands_create_success() {
    let conn = setup_db();

    let req = CreateCemeteryRequest {
        name: "Old Grave".to_string(),
        commune: Some("Lyon".to_string()),
        capacity: Some(500),
        municipality_id: None,
        address: Some("123 Rue des Morts".to_string()),
    };

    let result = internal_create_cemetery(&conn, req);
    assert!(result.is_ok());
    let created = result.unwrap();
    assert_eq!(created.name, "Old Grave");
    assert_eq!(created.capacity, Some(500));
}

#[test]
fn test_cemetery_commands_create_invalid_capacity() {
    let conn = setup_db();

    let req = CreateCemeteryRequest {
        name: "Bad Cemetery".to_string(),
        commune: None,
        capacity: Some(-10), // Invalid
        municipality_id: None,
        address: None,
    };

    let result = internal_create_cemetery(&conn, req);
    assert!(result.is_err());
    match result {
        Err(AppError::InvalidInput(msg)) => assert!(msg.contains("capacité")),
        _ => panic!("Expected InvalidInput error"),
    }
}

#[test]
fn test_cemetery_commands_create_duplicate_name() {
    let conn = setup_db();

    let req1 = CreateCemeteryRequest {
        name: "Saint Denis".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    internal_create_cemetery(&conn, req1.clone()).unwrap();

    let result = internal_create_cemetery(&conn, req1);
    assert!(result.is_err());
    match result {
        Err(AppError::Duplicate(msg)) => assert!(msg.contains("Saint Denis")),
        _ => panic!("Expected Duplicate error"),
    }
}

#[test]
fn test_cemetery_commands_create_normalization() {
    let conn = setup_db();

    let req1 = CreateCemeteryRequest {
        name: "Cemetery   With   Spaces".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    internal_create_cemetery(&conn, req1).unwrap();

    // Try with single spaces (should be duplicate due to normalization)
    let req2 = CreateCemeteryRequest {
        name: "Cemetery With Spaces".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let result = internal_create_cemetery(&conn, req2);
    assert!(result.is_err());
    match result {
        Err(AppError::Duplicate(_)) => {}
        _ => panic!("Expected Duplicate error"),
    }
}

#[test]
fn test_cemetery_commands_get_success() {
    let conn = setup_db();

    let req = CreateCemeteryRequest {
        name: "Grand Cimetière".to_string(),
        commune: Some("Paris".to_string()),
        capacity: Some(1000),
        municipality_id: None,
        address: None,
    };

    let created = internal_create_cemetery(&conn, req).unwrap();
    let retrieved = internal_get_cemetery(&conn, created.id);

    assert!(retrieved.is_ok());
    let retrieved = retrieved.unwrap();
    assert_eq!(retrieved.name, "Grand Cimetière");
    assert_eq!(retrieved.capacity, Some(1000));
}

#[test]
fn test_cemetery_commands_get_not_found() {
    let conn = setup_db();

    let result = internal_get_cemetery(&conn, 99999);
    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(msg)) => assert!(msg.contains("99999")),
        _ => panic!("Expected NotFound error"),
    }
}

#[test]
fn test_cemetery_commands_list() {
    let conn = setup_db();

    let req1 = CreateCemeteryRequest {
        name: "Cemetery 1".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let req2 = CreateCemeteryRequest {
        name: "Cemetery 2".to_string(),
        commune: None,
        capacity: Some(200),
        municipality_id: None,
        address: None,
    };

    internal_create_cemetery(&conn, req1).unwrap();
    internal_create_cemetery(&conn, req2).unwrap();

    let list = internal_list_cemeteries(&conn);
    assert!(list.is_ok());
    assert_eq!(list.unwrap().len(), 2);
}

#[test]
fn test_cemetery_commands_update_success() {
    let conn = setup_db();

    let req = CreateCemeteryRequest {
        name: "Original".to_string(),
        commune: Some("City".to_string()),
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let created = internal_create_cemetery(&conn, req).unwrap();

    let update_req = UpdateCemeteryRequest {
        name: Some("Updated".to_string()),
        commune: Some("NewCity".to_string()),
        capacity: Some(200),
        municipality_id: None,
        address: Some("456 Main St".to_string()),
        is_active: None,
    };

    let result = internal_update_cemetery(&conn, created.id, update_req);
    assert!(result.is_ok());
    let updated = result.unwrap();
    assert_eq!(updated.name, "Updated");
    assert_eq!(updated.capacity, Some(200));
}

#[test]
fn test_cemetery_commands_update_not_found() {
    let conn = setup_db();

    let update_req = UpdateCemeteryRequest {
        name: Some("Test".to_string()),
        commune: None,
        capacity: None,
        municipality_id: None,
        address: None,
        is_active: None,
    };

    let result = internal_update_cemetery(&conn, 99999, update_req);
    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(_)) => {}
        _ => panic!("Expected NotFound error"),
    }
}

#[test]
fn test_cemetery_commands_delete_soft_delete() {
    let conn = setup_db();

    let req = CreateCemeteryRequest {
        name: "To Inactivate".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let created = internal_create_cemetery(&conn, req).unwrap();
    let result = internal_delete_cemetery(&conn, created.id);

    assert!(result.is_ok());
    assert!(result.unwrap());

    // Verify it's soft-deleted (inactive) and not in list
    let list = internal_list_cemeteries(&conn).unwrap();
    assert!(list.is_empty());
}

#[test]
fn test_cemetery_commands_delete_not_found() {
    let conn = setup_db();

    let result = internal_delete_cemetery(&conn, 99999);
    assert!(result.is_err());
}

#[test]
fn test_cemetery_commands_transaction_rollback_on_duplicate() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");

    let req1 = CreateCemeteryRequest {
        name: "First".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    internal_create_cemetery(&conn, req1).unwrap();

    // Try to create with duplicate name
    let req2 = CreateCemeteryRequest {
        name: "First".to_string(),
        commune: None,
        capacity: Some(200),
        municipality_id: None,
        address: None,
    };

    let result = internal_create_cemetery(&conn, req2);
    assert!(result.is_err());
    match result {
        Err(AppError::Duplicate(_)) => {}
        _ => panic!("Expected Duplicate error"),
    }

    // Verify only first cemetery exists
    let list = internal_list_cemeteries(&conn).unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].name, "First");
}

#[test]
fn test_cemetery_commands_validation_differentiation() {
    let conn = setup_db();

    // Test validation error (negative capacity)
    let invalid_req = CreateCemeteryRequest {
        name: "Invalid".to_string(),
        commune: None,
        capacity: Some(-50),
        municipality_id: None,
        address: None,
    };

    let result = internal_create_cemetery(&conn, invalid_req);
    assert!(result.is_err());
    match result {
        Err(AppError::InvalidInput(_)) => {}
        _ => panic!("Expected InvalidInput error"),
    }

    // Test not found error
    let update_req = UpdateCemeteryRequest {
        name: Some("Test".to_string()),
        commune: None,
        capacity: None,
        municipality_id: None,
        address: None,
        is_active: None,
    };

    let result = internal_update_cemetery(&conn, 99999, update_req);
    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(_)) => {}
        _ => panic!("Expected NotFound error"),
    }
}

#[test]
fn test_cemetery_commands_soft_delete_reusable_name() {
    let conn = setup_db();

    let req1 = CreateCemeteryRequest {
        name: "Reusable Name".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let created1 = internal_create_cemetery(&conn, req1).unwrap();
    internal_delete_cemetery(&conn, created1.id).unwrap();

    // Should be able to create new cemetery with same name since first is inactive
    let req2 = CreateCemeteryRequest {
        name: "Reusable Name".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let result = internal_create_cemetery(&conn, req2);
    assert!(result.is_ok());
}

#[test]
fn test_cemetery_commands_case_insensitive_uniqueness() {
    let conn = setup_db();

    let req1 = CreateCemeteryRequest {
        name: "MY CEMETERY".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    internal_create_cemetery(&conn, req1).unwrap();

    // Try with different case
    let req2 = CreateCemeteryRequest {
        name: "my cemetery".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let result = internal_create_cemetery(&conn, req2);
    assert!(result.is_err());
    match result {
        Err(AppError::Duplicate(_)) => {}
        _ => panic!("Expected Duplicate error"),
    }
}

#[test]
fn test_cemetery_create_transaction_atomicity() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");

    // Create first cemetery successfully
    let req1 = CreateCemeteryRequest {
        name: "Valid Cemetery".to_string(),
        commune: Some("Paris".to_string()),
        capacity: Some(500),
        municipality_id: None,
        address: Some("123 Main St".to_string()),
    };

    let result1 = internal_create_cemetery(&conn, req1);
    assert!(result1.is_ok());
    let count_after_success = internal_list_cemeteries(&conn).unwrap().len();
    assert_eq!(count_after_success, 1);

    // Try to create with invalid capacity (should rollback entire transaction)
    let req2 = CreateCemeteryRequest {
        name: "Invalid Cemetery".to_string(),
        commune: None,
        capacity: Some(-100), // Invalid
        municipality_id: None,
        address: None,
    };

    let result2 = internal_create_cemetery(&conn, req2);
    assert!(result2.is_err());

    // Verify that count hasn't increased due to transaction rollback
    let count_after_error = internal_list_cemeteries(&conn).unwrap().len();
    assert_eq!(
        count_after_error, 1,
        "Transaction should have rolled back on validation error"
    );
}

#[test]
fn test_cemetery_update_transaction_atomicity() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");

    let req = CreateCemeteryRequest {
        name: "Original".to_string(),
        commune: Some("Original City".to_string()),
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let created = internal_create_cemetery(&conn, req).unwrap();
    let id = created.id;

    // Try to update with invalid capacity (should rollback)
    let invalid_update = UpdateCemeteryRequest {
        name: Some("Updated".to_string()),
        commune: None,
        capacity: Some(-200), // Invalid capacity
        municipality_id: None,
        address: None,
        is_active: None,
    };

    let result = internal_update_cemetery(&conn, id, invalid_update);
    assert!(result.is_err());

    // Verify original data hasn't changed
    let retrieved = internal_get_cemetery(&conn, id).unwrap();
    assert_eq!(retrieved.name, "Original");
    assert_eq!(retrieved.capacity, Some(100));
}
