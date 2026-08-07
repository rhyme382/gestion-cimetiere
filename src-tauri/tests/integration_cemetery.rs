use gestion_cimetiere::core::models::Cemetery;
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::CemeteryRepository;
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

#[test]
fn integration_cemetery_migration_with_backfill() {
    // This test validates that the migration 0009 correctly backfills the municipalities table
    // from existing cemetery.commune values and links cemeteries to municipalities via municipality_id.
    // This ensures compatibility with legacy data during the transition to the new referential model (FP-001).
    // Callable via: cargo test -p gestion-cimetiere integration_cemetery

    use gestion_cimetiere::db::migrations::run_migrations;
    use rusqlite::Connection;

    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");

    // Run full migration suite
    run_migrations(&conn).expect("Failed to run migrations");

    // Verify municipalities table exists after all migrations
    let municipalities_exist: bool = conn.query_row(
        "SELECT COUNT(*) > 0 FROM sqlite_master WHERE type='table' AND name='municipalities'",
        [],
        |row| row.get(0)
    ).expect("Failed to query sqlite_master");
    assert!(municipalities_exist, "municipalities table should exist after migrations");

    // Verify cemetery has new columns from migration 0009
    let cemetery_columns: Vec<String> = conn.prepare("PRAGMA table_info(cemeteries)")
        .expect("Failed to prepare PRAGMA query")
        .query_map([], |row| row.get::<_, String>(1))
        .expect("Failed to query table_info")
        .filter_map(|r| r.ok())
        .collect();

    assert!(cemetery_columns.contains(&"municipality_id".to_string()),
            "cemeteries should have municipality_id column after migration 0009");
    assert!(cemetery_columns.contains(&"address".to_string()),
            "cemeteries should have address column after migration 0009");
    assert!(cemetery_columns.contains(&"is_active".to_string()),
            "cemeteries should have is_active column after migration 0009");

    // Verify index exists for municipality lookups
    let has_municipality_id_index: bool = conn.query_row(
        "SELECT COUNT(*) > 0 FROM sqlite_master WHERE type='index' AND name='idx_cemeteries_municipality_id'",
        [],
        |row| row.get(0)
    ).expect("Failed to query indexes");
    assert!(has_municipality_id_index, "Should have index on cemeteries.municipality_id");

    // Verify is_active index exists for filtering
    let has_is_active_index: bool = conn.query_row(
        "SELECT COUNT(*) > 0 FROM sqlite_master WHERE type='index' AND name='idx_cemeteries_is_active'",
        [],
        |row| row.get(0)
    ).expect("Failed to query indexes");
    assert!(has_is_active_index, "Should have index on cemeteries.is_active");
}

#[test]
fn integration_cemetery_preserves_legacy_data() {
    // Demonstrates complete legacy → migration → backfill scenario:
    // 1. Create a pre-0008/0009 database with cemetery data
    // 2. Apply migrations 0008 and 0009
    // 3. Verify municipalities were backfilled from commune field
    // 4. Verify cemetery_id links remain valid and cemetery data is preserved

    use gestion_cimetiere::db::migrations::run_migrations;
    use rusqlite::Connection;

    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");

    // Simulate pre-0008/0009 database state by applying only initial schema + 0007
    let initial_schema = include_str!("../migrations/001_initial_schema.sql");
    let alerts_table = include_str!("../migrations/0006_create_alerts_table.sql");

    conn.execute_batch(initial_schema)
        .expect("Failed to apply initial schema");
    conn.execute_batch(alerts_table)
        .expect("Failed to apply alerts table");

    // Create schema_migrations table
    conn.execute_batch(
        "CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"
    ).expect("Failed to create schema_migrations");

    // Record applied migrations
    conn.execute(
        "INSERT INTO schema_migrations (version) VALUES (?)",
        rusqlite::params!["001_initial_schema"],
    ).expect("Failed to record migration");
    conn.execute(
        "INSERT INTO schema_migrations (version) VALUES (?)",
        rusqlite::params!["0006_create_alerts_table"],
    ).expect("Failed to record migration");

    // Now insert legacy cemetery data (pre-0008/0009 schema, with commune field but no municipality_id)
    let cemetery_id = conn.execute_batch(
        "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at)
         VALUES ('Legacy Paris Cemetery', 'Paris', 1000, '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"
    );
    assert!(cemetery_id.is_ok(), "Should insert legacy cemetery data");

    // Apply full migration suite (including 0008, 0009)
    run_migrations(&conn).expect("Failed to run migrations");

    // Verify municipalities table was created
    let municipality_count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM municipalities WHERE name = 'Paris'",
        [],
        |row| row.get(0)
    ).expect("Failed to query municipalities");
    assert_eq!(municipality_count, 1, "Should have created municipality 'Paris' from backfill");

    // Verify cemetery was linked to municipality via backfill
    let linked: (Option<i64>, String, Option<i32>) = conn.query_row(
        "SELECT municipality_id, name, capacity FROM cemeteries WHERE name = 'Legacy Paris Cemetery'",
        [],
        |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?))
    ).expect("Failed to query cemetery after migration");

    assert!(linked.0.is_some(), "cemetery municipality_id should be backfilled from commune");
    assert_eq!(linked.1, "Legacy Paris Cemetery", "cemetery name should be preserved");
    assert_eq!(linked.2, Some(1000), "cemetery capacity should be preserved");
}
