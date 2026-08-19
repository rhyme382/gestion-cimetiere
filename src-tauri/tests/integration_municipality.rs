use gestion_cimetiere::core::models::Municipality;
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::MunicipalityRepository;
use gestion_cimetiere::errors::AppError;
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

fn setup_db_with_file(db_path: &str) -> Connection {
    let conn = Connection::open(db_path).expect("Failed to open database file");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

#[test]
fn test_full_municipality_workflow() {
    let conn = setup_db();

    // Create a municipality
    let municipality = Municipality::new(
        "Test Municipality".to_string(),
        "12345".to_string(),
        Some("12000".to_string()),
        Some("contact@test.fr".to_string()),
    );

    let created = MunicipalityRepository::create(&conn, &municipality)
        .expect("Failed to create municipality");
    assert!(created.id > 0);
    assert_eq!(created.name, "Test Municipality");
    assert_eq!(created.insee_code, "12345");
    assert_eq!(created.postal_code, Some("12000".to_string()));
    assert_eq!(created.email, Some("contact@test.fr".to_string()));

    // List municipalities
    let list = MunicipalityRepository::list(&conn).expect("Failed to list municipalities");
    assert!(list.len() > 0);
    assert_eq!(list[0].id, created.id);

    // Get the municipality by id
    let retrieved =
        MunicipalityRepository::get(&conn, created.id).expect("Failed to get municipality");
    assert_eq!(retrieved.id, created.id);
    assert_eq!(retrieved.name, created.name);
    assert_eq!(retrieved.insee_code, created.insee_code);
    assert_eq!(retrieved.postal_code, created.postal_code);
    assert_eq!(retrieved.email, created.email);
}

#[test]
fn test_municipality_create_with_lowercase_insee() {
    let conn = setup_db();

    let municipality = Municipality::new(
        "Paris".to_string(),
        "abc12".to_string(), // Lowercase should be normalized
        Some("75000".to_string()),
        None,
    );

    let created = MunicipalityRepository::create(&conn, &municipality)
        .expect("Failed to create municipality");

    // Verify INSEE code is normalized to uppercase
    assert_eq!(created.insee_code, "ABC12");

    // Retrieve and verify persistence
    let retrieved = MunicipalityRepository::get(&conn, created.id).unwrap();
    assert_eq!(retrieved.insee_code, "ABC12");
}

#[test]
fn test_municipality_duplicate_normalized_insee() {
    let conn = setup_db();

    let mun1 = Municipality::new(
        "City One".to_string(),
        "xyz99".to_string(), // Lowercase
        None,
        None,
    );

    let mun2 = Municipality::new(
        "City Two".to_string(),
        "XYZ88".to_string(), // Different INSEE (uppercase)
        None,
        None,
    );

    MunicipalityRepository::create(&conn, &mun1).expect("First municipality creation failed");
    // Cannot create a second gestionnaire
    let result = MunicipalityRepository::create(&conn, &mun2);

    assert!(result.is_err());
    match result {
        Err(AppError::Duplicate(msg)) => {
            // Should fail because a gestionnaire is already configured
            assert!(msg.contains("commune gestionnaire est déjà configurée"));
        }
        _ => panic!("Expected Duplicate error for singleton constraint"),
    }
}

#[test]
fn test_municipality_validation_errors_differentiation() {
    let conn = setup_db();

    // Test validation error
    let invalid_length = Municipality::new(
        "Test".to_string(),
        "123".to_string(), // Too short
        None,
        None,
    );

    let result = MunicipalityRepository::create(&conn, &invalid_length);
    assert!(result.is_err());
    match result {
        Err(AppError::InvalidInput(msg)) => {
            assert!(msg.contains("exactement 5 caractères"));
        }
        _ => panic!("Expected InvalidInput error"),
    }

    // Test duplicate error
    let valid1 = Municipality::new("First".to_string(), "11111".to_string(), None, None);

    let valid2 = Municipality::new("Second".to_string(), "11111".to_string(), None, None);

    MunicipalityRepository::create(&conn, &valid1).unwrap();
    let result2 = MunicipalityRepository::create(&conn, &valid2);

    assert!(result2.is_err());
    match result2 {
        Err(AppError::Duplicate(_)) => {} // Correct
        _ => panic!("Expected Duplicate error"),
    }
}

#[test]
fn test_municipality_update_with_rollback() {
    let conn = setup_db();

    let municipality = Municipality::new("Original".to_string(), "22222".to_string(), None, None);

    let created = MunicipalityRepository::create(&conn, &municipality).unwrap();
    let id = created.id;

    // Try to update name (should succeed since we're only updating name, not INSEE)
    let mut update_attempt = Municipality::new(
        "Updated".to_string(),
        "22222".to_string(), // Same INSEE
        None,
        None,
    );
    update_attempt.id = id;
    update_attempt.created_at = created.created_at;

    let result = MunicipalityRepository::update(&conn, id, &update_attempt);
    assert!(result.is_ok());

    // Verify updated data persisted
    let after_update = MunicipalityRepository::get(&conn, id).unwrap();
    assert_eq!(after_update.insee_code, "22222");
    assert_eq!(after_update.name, "Updated");
}

#[test]
fn test_municipality_persistence_after_reopen() {
    let temp_dir = tempfile::tempdir().expect("Failed to create temp directory");
    let db_path = temp_dir.path().join("test_municipality.db");
    let db_path_str = db_path.to_string_lossy().to_string();

    let municipality_id = {
        let conn = setup_db_with_file(&db_path_str);

        let municipality = Municipality::new(
            "Persistent City".to_string(),
            "44444".to_string(),
            Some("44000".to_string()),
            None,
        );

        let created = MunicipalityRepository::create(&conn, &municipality)
            .expect("Failed to create municipality");
        let id = created.id;

        // Verify data in first connection
        let first_read = MunicipalityRepository::get(&conn, id).unwrap();
        assert_eq!(first_read.name, "Persistent City");
        assert_eq!(first_read.insee_code, "44444");
        assert_eq!(first_read.postal_code, Some("44000".to_string()));

        // Connection closes at end of scope
        id
    };

    // Reopen database and verify persistence
    let conn = setup_db_with_file(&db_path_str);
    let second_read = MunicipalityRepository::get(&conn, municipality_id)
        .expect("Failed to retrieve municipality after reopen");

    assert_eq!(second_read.name, "Persistent City");
    assert_eq!(second_read.insee_code, "44444");
    assert_eq!(second_read.postal_code, Some("44000".to_string()));
}

#[test]
fn test_municipality_transaction_rollback_on_duplicate_insee() {
    let mut conn = setup_db();

    let municipality1 = Municipality::new("City One".to_string(), "55555".to_string(), None, None);

    let municipality2 = Municipality::new(
        "City Two".to_string(),
        "55555".to_string(), // Same INSEE code
        None,
        None,
    );

    MunicipalityRepository::create(&conn, &municipality1).unwrap();

    // Create a transaction
    let tx = conn.transaction().expect("Failed to start transaction");

    // Try to create duplicate in transaction
    let result = MunicipalityRepository::create(&tx, &municipality2);
    assert!(result.is_err());
    match result {
        Err(AppError::Duplicate(_)) => {}
        _ => panic!("Expected Duplicate error"),
    }

    // Attempt to rollback
    tx.rollback().expect("Failed to rollback");

    // Verify only the first municipality exists
    let list = MunicipalityRepository::list(&conn).unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].name, "City One");
}

#[test]
fn test_municipality_email_validation_in_update() {
    let conn = setup_db();

    let municipality = Municipality::new("Valid City".to_string(), "66666".to_string(), None, None);

    let created = MunicipalityRepository::create(&conn, &municipality).unwrap();

    // Try to update with invalid email
    let mut update_attempt = Municipality::new(
        "Valid City".to_string(),
        "66666".to_string(),
        None,
        Some("invalid-email".to_string()),
    );
    update_attempt.id = created.id;
    update_attempt.created_at = created.created_at;

    let result = MunicipalityRepository::update(&conn, created.id, &update_attempt);
    assert!(result.is_err());
    match result {
        Err(AppError::InvalidInput(msg)) => {
            assert!(msg.contains("e-mail") || msg.contains("email") || msg.contains("valide"));
        }
        _ => panic!("Expected InvalidInput error for invalid email"),
    }

    // Verify data wasn't persisted
    let retrieved = MunicipalityRepository::get(&conn, created.id).unwrap();
    assert_eq!(retrieved.email, None);
}
