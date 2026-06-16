use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::IndividualRepository;
use gestion_cimetiere::core::models::Individual;
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

#[test]
fn test_full_individual_workflow() {
    let conn = setup_db();

    // Create an individual
    let individual = Individual::new(
        "Jean Dupont".to_string(),
        Some("jean@example.com".to_string()),
        Some("06 12 34 56 78".to_string()),
        "family_member".to_string(),
    );

    let created = IndividualRepository::create(&conn, &individual)
        .expect("Failed to create individual");
    assert!(created.id > 0);
    assert_eq!(created.name, "Jean Dupont");
    assert_eq!(created.email, Some("jean@example.com".to_string()));
    assert_eq!(created.phone, Some("06 12 34 56 78".to_string()));
    assert_eq!(created.role, "family_member");

    // List individuals
    let list = IndividualRepository::list(&conn).expect("Failed to list individuals");
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].id, created.id);

    // Get individual by id
    let retrieved = IndividualRepository::get(&conn, created.id)
        .expect("Failed to get individual");
    assert_eq!(retrieved.id, created.id);
    assert_eq!(retrieved.name, created.name);
    assert_eq!(retrieved.email, created.email);
}

#[test]
fn test_individual_create_and_list() {
    let conn = setup_db();

    let individual1 = Individual::new(
        "Alice Martin".to_string(),
        Some("alice@example.com".to_string()),
        None,
        "relative".to_string(),
    );
    let individual2 = Individual::new(
        "Bob Durand".to_string(),
        None,
        Some("06 98 76 54 32".to_string()),
        "owner".to_string(),
    );
    let individual3 = Individual::new(
        "Charlie Bernard".to_string(),
        None,
        None,
        "visitor".to_string(),
    );

    IndividualRepository::create(&conn, &individual1).unwrap();
    IndividualRepository::create(&conn, &individual2).unwrap();
    IndividualRepository::create(&conn, &individual3).unwrap();

    let list = IndividualRepository::list(&conn).unwrap();
    assert_eq!(list.len(), 3);

    // Ordered by name
    assert_eq!(list[0].name, "Alice Martin");
    assert_eq!(list[1].name, "Bob Durand");
    assert_eq!(list[2].name, "Charlie Bernard");
}

#[test]
fn test_individual_update() {
    let conn = setup_db();

    let individual = Individual::new(
        "Original Name".to_string(),
        Some("original@example.com".to_string()),
        Some("06 11 22 33 44".to_string()),
        "family_member".to_string(),
    );

    let created = IndividualRepository::create(&conn, &individual).unwrap();
    let id = created.id;

    let mut updated_individual = Individual::new(
        "Updated Name".to_string(),
        Some("updated@example.com".to_string()),
        Some("06 99 88 77 66".to_string()),
        "owner".to_string(),
    );
    updated_individual.id = id;

    let updated = IndividualRepository::update(&conn, id, &updated_individual).unwrap();
    assert_eq!(updated.id, id);
    assert_eq!(updated.name, "Updated Name");
    assert_eq!(updated.email, Some("updated@example.com".to_string()));
    assert_eq!(updated.phone, Some("06 99 88 77 66".to_string()));
    assert_eq!(updated.role, "owner");

    // Verify persistence
    let retrieved = IndividualRepository::get(&conn, id).unwrap();
    assert_eq!(retrieved.name, "Updated Name");
    assert_eq!(retrieved.email, Some("updated@example.com".to_string()));
}


#[test]
fn test_individual_search() {
    let conn = setup_db();

    let individual1 = Individual::new(
        "David Smith".to_string(),
        Some("david@example.com".to_string()),
        None,
        "family_member".to_string(),
    );
    let individual2 = Individual::new(
        "Emma Johnson".to_string(),
        None,
        Some("06 12 34 56 78".to_string()),
        "owner".to_string(),
    );
    let individual3 = Individual::new(
        "Frank Davis".to_string(),
        None,
        None,
        "visitor".to_string(),
    );

    IndividualRepository::create(&conn, &individual1).unwrap();
    IndividualRepository::create(&conn, &individual2).unwrap();
    IndividualRepository::create(&conn, &individual3).unwrap();

    // Search by name pattern
    let results = IndividualRepository::search(&conn, "D").unwrap();
    assert_eq!(results.len(), 2); // David Smith and Frank Davis

    let results = IndividualRepository::search(&conn, "Smith").unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].name, "David Smith");

    // Search by email
    let results = IndividualRepository::search(&conn, "david@").unwrap();
    assert_eq!(results.len(), 1);

    // Search by phone
    let results = IndividualRepository::search(&conn, "06 12").unwrap();
    assert_eq!(results.len(), 1);
}

#[test]
fn test_individual_with_optional_fields() {
    let conn = setup_db();

    let individual_full = Individual::new(
        "Complete Person".to_string(),
        Some("complete@example.com".to_string()),
        Some("06 11 22 33 44".to_string()),
        "owner".to_string(),
    );

    let individual_partial = Individual::new(
        "Partial Person".to_string(),
        None,
        None,
        "visitor".to_string(),
    );

    let created_full = IndividualRepository::create(&conn, &individual_full).unwrap();
    let created_partial = IndividualRepository::create(&conn, &individual_partial).unwrap();

    assert_eq!(created_full.email, Some("complete@example.com".to_string()));
    assert_eq!(created_full.phone, Some("06 11 22 33 44".to_string()));

    assert_eq!(created_partial.email, None);
    assert_eq!(created_partial.phone, None);

    // Verify both are retrievable
    let retrieved_full = IndividualRepository::get(&conn, created_full.id).unwrap();
    let retrieved_partial = IndividualRepository::get(&conn, created_partial.id).unwrap();

    assert_eq!(retrieved_full.email.is_some(), true);
    assert_eq!(retrieved_partial.email.is_none(), true);
}
