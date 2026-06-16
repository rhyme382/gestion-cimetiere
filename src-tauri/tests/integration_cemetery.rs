use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::CemeteryRepository;
use gestion_cimetiere::core::models::Cemetery;
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

#[test]
fn test_full_cemetery_workflow() {
    let conn = setup_db();

    // Create a cemetery
    let cemetery = Cemetery::new(
        "Integration Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(1000),
    );

    let created = CemeteryRepository::create(&conn, &cemetery).expect("Failed to create cemetery");
    assert!(created.id > 0);
    assert_eq!(created.name, "Integration Test Cemetery");
    assert_eq!(created.commune, Some("Paris".to_string()));
    assert_eq!(created.capacity, Some(1000));

    // List cemeteries
    let list = CemeteryRepository::list(&conn).expect("Failed to list cemeteries");
    assert!(list.len() > 0);
    assert_eq!(list[0].id, created.id);

    // Get the cemetery by id
    let retrieved = CemeteryRepository::get(&conn, created.id).expect("Failed to get cemetery");
    assert_eq!(retrieved.id, created.id);
    assert_eq!(retrieved.name, created.name);
    assert_eq!(retrieved.commune, created.commune);
    assert_eq!(retrieved.capacity, created.capacity);
}

#[test]
fn test_cemetery_create_and_list() {
    let conn = setup_db();

    let cemetery1 = Cemetery::new(
        "Cemetery A".to_string(),
        Some("Lyon".to_string()),
        Some(500),
    );
    let cemetery2 = Cemetery::new(
        "Cemetery B".to_string(),
        Some("Marseille".to_string()),
        Some(750),
    );

    let created1 = CemeteryRepository::create(&conn, &cemetery1).unwrap();
    let created2 = CemeteryRepository::create(&conn, &cemetery2).unwrap();

    let list = CemeteryRepository::list(&conn).unwrap();
    assert_eq!(list.len(), 2);

    // Most recent first (created2 then created1)
    assert_eq!(list[0].id, created2.id);
    assert_eq!(list[1].id, created1.id);
}

#[test]
fn test_cemetery_update() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Original Cemetery".to_string(),
        Some("Toulouse".to_string()),
        Some(300),
    );

    let created = CemeteryRepository::create(&conn, &cemetery).unwrap();
    let id = created.id;

    let mut updated_cemetery = Cemetery::new(
        "Updated Cemetery".to_string(),
        Some("Nice".to_string()),
        Some(450),
    );
    updated_cemetery.id = id;

    let updated = CemeteryRepository::update(&conn, id, &updated_cemetery).unwrap();
    assert_eq!(updated.id, id);
    assert_eq!(updated.name, "Updated Cemetery");
    assert_eq!(updated.commune, Some("Nice".to_string()));
    assert_eq!(updated.capacity, Some(450));

    // Verify persistence
    let retrieved = CemeteryRepository::get(&conn, id).unwrap();
    assert_eq!(retrieved.name, "Updated Cemetery");
}

#[test]
fn test_cemetery_delete() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "To Be Deleted".to_string(),
        Some("Nantes".to_string()),
        Some(200),
    );

    let created = CemeteryRepository::create(&conn, &cemetery).unwrap();
    let id = created.id;

    // Verify it exists
    let result = CemeteryRepository::get(&conn, id);
    assert!(result.is_ok());

    // Delete it
    let deleted = CemeteryRepository::delete(&conn, id).unwrap();
    assert!(deleted);

    // Verify it no longer exists
    let result = CemeteryRepository::get(&conn, id);
    assert!(result.is_err());
}
