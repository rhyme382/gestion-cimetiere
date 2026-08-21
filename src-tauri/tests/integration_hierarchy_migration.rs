use gestion_cimetiere::core::models::{Cemetery, Plot};
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{CemeteryRepository, PlotRepository};
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

#[test]
fn test_migration_creates_hierarchy_tables() {
    let conn = setup_db();

    // Verify that all hierarchy tables exist
    let result = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('sections', 'squares', 'rows')",
        [],
        |row| row.get::<_, i64>(0),
    );

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 3, "All hierarchy tables should exist");
}

#[test]
fn test_migration_adds_row_id_to_plots() {
    let conn = setup_db();

    // Verify that plots table has row_id column
    let result = conn.query_row(
        "PRAGMA table_info(plots)",
        [],
        |_| Ok(()),
    );

    assert!(result.is_ok());

    // Query the schema to confirm row_id exists
    let has_row_id: i64 = conn.query_row(
        "SELECT COUNT(*) FROM pragma_table_info('plots') WHERE name='row_id'",
        [],
        |row| row.get(0),
    ).unwrap();

    assert_eq!(has_row_id, 1, "plots table should have row_id column");
}

#[test]
fn test_migration_adds_administrative_reference_to_plots() {
    let conn = setup_db();

    // Verify that plots table has administrative_reference column
    let has_admin_ref: i64 = conn.query_row(
        "SELECT COUNT(*) FROM pragma_table_info('plots') WHERE name='administrative_reference'",
        [],
        |row| row.get(0),
    ).unwrap();

    assert_eq!(
        has_admin_ref, 1,
        "plots table should have administrative_reference column"
    );
}

#[test]
fn test_migration_is_idempotent() {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");

    // Run migrations first time
    run_migrations(&conn).expect("Failed to run migrations first time");

    // Count tables after first migration
    let count_after_first: i64 = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'",
        [],
        |row| row.get(0),
    ).unwrap();

    // Run migrations again (should be idempotent)
    run_migrations(&conn).expect("Failed to run migrations second time");

    // Count tables after second migration
    let count_after_second: i64 = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'",
        [],
        |row| row.get(0),
    ).unwrap();

    // Should be the same
    assert_eq!(
        count_after_first, count_after_second,
        "Migration should be idempotent"
    );
}

#[test]
fn test_hierarchy_uniqueness_per_parent() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create two sections with unique codes in the same cemetery
    conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, "SECTION_A", "Section A"],
    ).unwrap();

    conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, "SECTION_B", "Section B"],
    ).unwrap();

    let sections = PlotRepository::list_sections(&conn, created_cemetery.id).unwrap();
    assert_eq!(sections.len(), 2);

    // Try to create a duplicate section code in the same cemetery (should fail)
    let duplicate_result = conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, "SECTION_A", "Duplicate Section A"],
    );

    assert!(
        duplicate_result.is_err(),
        "Should not allow duplicate section codes in the same cemetery"
    );
}

#[test]
fn test_normalized_code_validation_on_insert() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Try to insert a section with leading spaces (should fail due to trigger)
    let result = conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, " SECTION_A", "Section with leading space"],
    );

    assert!(
        result.is_err(),
        "Should reject section code with leading spaces"
    );
}

#[test]
fn test_normalized_code_case_enforcement() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Try to insert a section with lowercase code (should fail due to trigger)
    let result = conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, "section_a", "Section A"],
    );

    assert!(
        result.is_err(),
        "Should reject section code that is not uppercase"
    );
}

#[test]
fn test_administrative_reference_auto_generation() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        1,
    );

    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    // Verify that administrative_reference was auto-generated
    assert!(created_plot.administrative_reference.is_some());
    let admin_ref = created_plot.administrative_reference.unwrap();
    assert_eq!(admin_ref, format!("EMP-{}", created_plot.id));
}

#[test]
fn test_administrative_reference_uniqueness_per_cemetery() {
    let conn = setup_db();

    // Create two cemeteries
    let cemetery1 = Cemetery::new(
        "Cemetery 1".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery1 = CemeteryRepository::create(&conn, &cemetery1).unwrap();

    let cemetery2 = Cemetery::new(
        "Cemetery 2".to_string(),
        Some("Lyon".to_string()),
        Some(100),
    );
    let created_cemetery2 = CemeteryRepository::create(&conn, &cemetery2).unwrap();

    // Create a plot in cemetery1
    let plot1 = Plot::new(
        created_cemetery1.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        1,
    );
    let created_plot1 = PlotRepository::create(&conn, &plot1).unwrap();

    // Create a plot in cemetery2
    let plot2 = Plot::new(
        created_cemetery2.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        1,
    );
    let created_plot2 = PlotRepository::create(&conn, &plot2).unwrap();

    // Both should have the same administrative_reference format (EMP-ID) because they're in different cemeteries
    // This is expected since the ID is globally unique across plots
    let admin_ref1 = created_plot1.administrative_reference.clone();
    let admin_ref2 = created_plot2.administrative_reference.clone();

    assert_ne!(admin_ref1, admin_ref2, "Different plots should have different administrative_reference values");
}

#[test]
fn test_plot_row_id_cemetery_mismatch_prevented() {
    let conn = setup_db();

    // Create two cemeteries
    let cemetery1 = Cemetery::new(
        "Cemetery 1".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery1 = CemeteryRepository::create(&conn, &cemetery1).unwrap();

    let cemetery2 = Cemetery::new(
        "Cemetery 2".to_string(),
        Some("Lyon".to_string()),
        Some(100),
    );
    let created_cemetery2 = CemeteryRepository::create(&conn, &cemetery2).unwrap();

    // Create hierarchy in cemetery2
    let section_id: i64 = conn.query_row(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![created_cemetery2.id, "SECTION_A", "Section A"],
        |row| row.get(0)
    ).unwrap();

    let square_id: i64 = conn.query_row(
        "INSERT INTO squares (section_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![section_id, "GENERAL", "General"],
        |row| row.get(0)
    ).unwrap();

    let row_id: i64 = conn.query_row(
        "INSERT INTO rows (square_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![square_id, "1", "Row 1"],
        |row| row.get(0)
    ).unwrap();

    // Try to create a plot in cemetery1 that references row from cemetery2 (should fail)
    let result = conn.execute(
        "INSERT INTO plots (cemetery_id, section, row, number, capacity, row_id, administrative_reference, status, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![
            created_cemetery1.id,
            Some("A"),
            Some(1),
            Some(1),
            1,
            Some(row_id),
            "EMP-TEST",
            "available"
        ],
    );

    assert!(
        result.is_err(),
        "Should not allow plot in one cemetery to reference hierarchy from another cemetery"
    );
}

#[test]
fn test_hierarchical_path_completeness() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create full hierarchy
    let section_id: i64 = conn.query_row(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![created_cemetery.id, "SECTION_A", "Section A"],
        |row| row.get(0)
    ).unwrap();

    let square_id: i64 = conn.query_row(
        "INSERT INTO squares (section_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![section_id, "GENERAL", "General"],
        |row| row.get(0)
    ).unwrap();

    let row_id: i64 = conn.query_row(
        "INSERT INTO rows (square_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![square_id, "1", "Row 1"],
        |row| row.get(0)
    ).unwrap();

    // Create plot with full hierarchy
    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        1,
    );

    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    // Link to hierarchy
    conn.execute(
        "UPDATE plots SET row_id = ? WHERE id = ?",
        rusqlite::params![row_id, created_plot.id],
    ).unwrap();

    // Retrieve and verify hierarchical_path
    let retrieved = PlotRepository::get(&conn, created_plot.id).unwrap();

    assert!(retrieved.hierarchical_path.is_some());
    let path = retrieved.hierarchical_path.unwrap();

    assert_eq!(path.section_id, Some(section_id));
    assert_eq!(path.section_code, Some("SECTION_A".to_string()));
    assert_eq!(path.section_label, Some("Section A".to_string()));
    assert_eq!(path.square_id, Some(square_id));
    assert_eq!(path.square_code, Some("GENERAL".to_string()));
    assert_eq!(path.square_label, Some("General".to_string()));
    assert_eq!(path.row_id, Some(row_id));
    assert_eq!(path.row_code, Some("1".to_string()));
    assert_eq!(path.row_label, Some("Row 1".to_string()));
}

#[test]
fn test_backward_compatibility_plots_without_row_id() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create plot without row_id (backward compatibility)
    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(5),
        1,
    );

    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    // Verify plot was created successfully
    assert!(created_plot.id > 0);

    // Verify administrative_reference is set
    assert!(created_plot.administrative_reference.is_some());

    // Verify hierarchical_path is None (no row_id)
    assert_eq!(created_plot.hierarchical_path, None);

    // Retrieve and verify persistence
    let retrieved = PlotRepository::get(&conn, created_plot.id).unwrap();
    assert_eq!(retrieved.section, Some("A".to_string()));
    assert_eq!(retrieved.row, Some(1));
    assert_eq!(retrieved.number, Some(5));
    assert_eq!(retrieved.hierarchical_path, None);
}
