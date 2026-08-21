use gestion_cimetiere::core::models::{Cemetery, Plot};
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{CemeteryRepository, PlotRepository};
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
fn test_full_plot_workflow() {
    let conn = setup_db();

    // Create a cemetery first
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(1000),
    );
    let created_cemetery =
        CemeteryRepository::create(&conn, &cemetery).expect("Failed to create cemetery");

    // Create a plot
    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        10,
    );

    let created_plot = PlotRepository::create(&conn, &plot).expect("Failed to create plot");
    assert!(created_plot.id > 0);
    assert_eq!(created_plot.cemetery_id, created_cemetery.id);
    assert_eq!(created_plot.section, Some("A".to_string()));
    assert_eq!(created_plot.row, Some(1));
    assert_eq!(created_plot.number, Some(1));
    assert_eq!(created_plot.capacity, 10);
    assert_eq!(created_plot.status, "available");

    // List plots for the cemetery
    let list = PlotRepository::list(&conn, created_cemetery.id).expect("Failed to list plots");
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].id, created_plot.id);

    // Get plot by id
    let retrieved = PlotRepository::get(&conn, created_plot.id).expect("Failed to get plot");
    assert_eq!(retrieved.id, created_plot.id);
    assert_eq!(retrieved.cemetery_id, created_cemetery.id);
}

#[test]
fn test_plot_create_and_list() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Lyon".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot1 = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        5,
    );
    let plot2 = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(2),
        5,
    );
    let plot3 = Plot::new(
        created_cemetery.id,
        Some("B".to_string()),
        Some(1),
        Some(1),
        8,
    );

    PlotRepository::create(&conn, &plot1).unwrap();
    PlotRepository::create(&conn, &plot2).unwrap();
    PlotRepository::create(&conn, &plot3).unwrap();

    let list = PlotRepository::list(&conn, created_cemetery.id).unwrap();
    assert_eq!(list.len(), 3);
    // Ordered by section, row, number
    assert_eq!(list[0].section, Some("A".to_string()));
    assert_eq!(list[0].number, Some(1));
    assert_eq!(list[1].number, Some(2));
    assert_eq!(list[2].section, Some("B".to_string()));
}

#[test]
fn test_plot_update() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Marseille".to_string()),
        None,
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot = Plot::new(
        created_cemetery.id,
        Some("C".to_string()),
        Some(5),
        Some(10),
        12,
    );

    let created = PlotRepository::create(&conn, &plot).unwrap();
    let id = created.id;

    let mut updated_plot = Plot::new(
        created_cemetery.id,
        Some("D".to_string()),
        Some(6),
        Some(11),
        15,
    );
    updated_plot.id = id;
    updated_plot.status = "occupied".to_string();

    let updated = PlotRepository::update(&conn, id, &updated_plot).unwrap();
    assert_eq!(updated.id, id);
    assert_eq!(updated.section, Some("D".to_string()));
    assert_eq!(updated.row, Some(6));
    assert_eq!(updated.number, Some(11));
    assert_eq!(updated.capacity, 15);
    assert_eq!(updated.status, "occupied");

    // Verify persistence
    let retrieved = PlotRepository::get(&conn, id).unwrap();
    assert_eq!(retrieved.section, Some("D".to_string()));
    assert_eq!(retrieved.status, "occupied");
}

#[test]
fn test_plot_empty_list_for_cemetery() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Empty Cemetery".to_string(),
        Some("Strasbourg".to_string()),
        None,
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let list = PlotRepository::list(&conn, created_cemetery.id).unwrap();
    assert_eq!(list.len(), 0);
}

#[test]
fn test_plot_has_administrative_reference() {
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

    // Verify administrative_reference is set (auto-generated as EMP-{id})
    assert!(created_plot.administrative_reference.is_some());
    let admin_ref = created_plot.administrative_reference.unwrap();
    assert!(admin_ref.starts_with("EMP-"));

    // Verify persistence on get
    let retrieved = PlotRepository::get(&conn, created_plot.id).unwrap();
    assert_eq!(retrieved.administrative_reference, Some(admin_ref.clone()));
}

#[test]
fn test_plot_hierarchical_path_none_without_row_id() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create plot after migration (won't have row_id set automatically)
    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(5),
        1,
    );

    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    // Plots created after migration without explicit row_id won't have hierarchical_path
    // This is expected behavior - hierarchical_path is only populated if row_id is set
    assert_eq!(created_plot.hierarchical_path, None);

    // Administrative reference should still be set
    assert!(created_plot.administrative_reference.is_some());

    // Verify on get
    let retrieved = PlotRepository::get(&conn, created_plot.id).unwrap();
    assert_eq!(retrieved.hierarchical_path, None);
    assert!(retrieved.administrative_reference.is_some());
}

#[test]
fn test_list_sections_for_cemetery() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Manually create hierarchy entries for testing (simulating what migration does)
    // Create a section
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

    // Should have the two sections we created
    assert_eq!(sections.len(), 2);

    // Each section should have an id, normalized_code, and display_label
    for (id, code, label) in sections {
        assert!(id > 0);
        assert!(!code.is_empty());
        assert!(!label.is_empty());
    }
}

#[test]
fn test_list_squares_for_section() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Manually create hierarchy: section -> square
    conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, "SECTION_A", "Section A"],
    ).unwrap();

    // Get the section id we just created
    let section_id: i64 = conn.query_row(
        "SELECT id FROM sections WHERE cemetery_id = ? AND normalized_code = ?",
        rusqlite::params![created_cemetery.id, "SECTION_A"],
        |row| row.get(0)
    ).unwrap();

    // Create squares under this section
    conn.execute(
        "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![section_id, "GENERAL", "Général"],
    ).unwrap();

    conn.execute(
        "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![section_id, "ADVANCED", "Avancé"],
    ).unwrap();

    let squares = PlotRepository::list_squares(&conn, section_id).unwrap();

    // Should have the two squares we created
    assert_eq!(squares.len(), 2);

    for (id, code, label) in squares {
        assert!(id > 0);
        assert!(!code.is_empty());
        assert!(!label.is_empty());
    }
}

#[test]
fn test_list_rows_for_square() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Manually create full hierarchy: section -> square -> row
    conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, "SECTION_A", "Section A"],
    ).unwrap();

    let section_id: i64 = conn.query_row(
        "SELECT id FROM sections WHERE cemetery_id = ? AND normalized_code = ?",
        rusqlite::params![created_cemetery.id, "SECTION_A"],
        |row| row.get(0)
    ).unwrap();

    conn.execute(
        "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![section_id, "GENERAL", "Général"],
    ).unwrap();

    let square_id: i64 = conn.query_row(
        "SELECT id FROM squares WHERE section_id = ?",
        [section_id],
        |row| row.get(0)
    ).unwrap();

    // Create rows under the square
    conn.execute(
        "INSERT INTO rows (square_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![square_id, "1", "Rangée 1"],
    ).unwrap();

    conn.execute(
        "INSERT INTO rows (square_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![square_id, "2", "Rangée 2"],
    ).unwrap();

    let rows = PlotRepository::list_rows(&conn, square_id).unwrap();

    // Should have the two rows we created
    assert_eq!(rows.len(), 2);

    for (id, code, label) in rows {
        assert!(id > 0);
        assert!(!code.is_empty());
        assert!(!label.is_empty());
    }
}

#[test]
fn test_get_plot_not_found_with_typed_error() {
    let conn = setup_db();

    let result = PlotRepository::get(&conn, 99999);

    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(msg)) => {
            // Should contain the plot not found marker
            assert!(msg.contains("PLOT_NOT_FOUND") || msg.contains("99999"));
        }
        Err(AppError::Database(_)) => {
            panic!("Should return NotFound, not Database error");
        }
        Err(_) => {
            panic!("Should return NotFound error variant");
        }
        Ok(_) => {
            panic!("Should return an error for non-existent plot");
        }
    }
}

#[test]
fn test_list_sections_with_nonexistent_cemetery() {
    let conn = setup_db();

    let result = PlotRepository::list_sections(&conn, 99999);

    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(msg)) => {
            assert!(msg.contains("99999"));
        }
        _ => panic!("Should return NotFound error for non-existent cemetery"),
    }
}

#[test]
fn test_list_sections_with_existing_cemetery_no_sections() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Should return empty list, not error
    let sections = PlotRepository::list_sections(&conn, created_cemetery.id).unwrap();
    assert_eq!(sections.len(), 0);
}

#[test]
fn test_list_squares_with_nonexistent_section() {
    let conn = setup_db();

    let result = PlotRepository::list_squares(&conn, 99999);

    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(msg)) => {
            assert!(msg.contains("99999"));
        }
        _ => panic!("Should return NotFound error for non-existent section"),
    }
}

#[test]
fn test_list_rows_with_nonexistent_square() {
    let conn = setup_db();

    let result = PlotRepository::list_rows(&conn, 99999);

    assert!(result.is_err());
    match result {
        Err(AppError::NotFound(msg)) => {
            assert!(msg.contains("99999"));
        }
        _ => panic!("Should return NotFound error for non-existent square"),
    }
}

#[test]
fn test_administrative_reference_persistence_across_close_reopen() {
    // Use a temp file path that we control
    let temp_dir = std::env::temp_dir();
    let temp_path = temp_dir.join("test_cemetery_persistence.db");
    let temp_path_str = temp_path.to_string_lossy().to_string();

    // Clean up any previous test file
    std::fs::remove_file(&temp_path).ok();

    // First connection: create data
    {
        let conn = Connection::open(&temp_path_str).expect("Failed to open database");
        conn.execute("PRAGMA foreign_keys = ON", []).expect("Failed to enable foreign keys");
        run_migrations(&conn).expect("Failed to run migrations");

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
            Some(5),
            1,
        );

        let created_plot = PlotRepository::create(&conn, &plot).unwrap();
        let admin_ref = created_plot.administrative_reference.as_ref().map(|s| s.clone());

        // Verify administrative_reference is set
        assert!(admin_ref.is_some());
    }

    // Second connection: verify data persistence
    {
        let conn = Connection::open(&temp_path_str).expect("Failed to reopen database");
        conn.execute("PRAGMA foreign_keys = ON", []).expect("Failed to enable foreign keys");

        // Retrieve the plot (should be plot id 1)
        let retrieved = PlotRepository::get(&conn, 1).unwrap();

        // Verify administrative_reference persists
        assert!(retrieved.administrative_reference.is_some(), "Administrative reference should persist");

        // Should be EMP-1 for the first plot
        assert_eq!(retrieved.administrative_reference.as_ref().map(|s| s.as_str()), Some("EMP-1"));
    }

    // Clean up
    std::fs::remove_file(&temp_path).ok();
}

#[test]
fn test_hierarchical_path_persistence_across_close_reopen() {
    // Use a temp file path that we control
    let temp_dir = std::env::temp_dir();
    let temp_path = temp_dir.join("test_hierarchy_persistence.db");
    let temp_path_str = temp_path.to_string_lossy().to_string();

    // Clean up any previous test file
    std::fs::remove_file(&temp_path).ok();

    let (section_id, square_id, row_id, plot_id) = {
        // First connection: create full hierarchy and plot
        let conn = Connection::open(&temp_path_str).expect("Failed to open database");
        conn.execute("PRAGMA foreign_keys = ON", []).expect("Failed to enable foreign keys");
        run_migrations(&conn).expect("Failed to run migrations");

        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Paris".to_string()),
            Some(100),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a full hierarchy: section -> square -> row
        let section_id_val: i64 = conn.query_row(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
            rusqlite::params![created_cemetery.id, "SECTION_A", "Section A"],
            |row| row.get(0)
        ).unwrap();

        let square_id_val: i64 = conn.query_row(
            "INSERT INTO squares (section_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
            rusqlite::params![section_id_val, "GENERAL", "General Square"],
            |row| row.get(0)
        ).unwrap();

        let row_id_val: i64 = conn.query_row(
            "INSERT INTO rows (square_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
            rusqlite::params![square_id_val, "1", "Row 1"],
            |row| row.get(0)
        ).unwrap();

        // Create a plot linked to this row
        let plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(1),
            1,
        );

        let created_plot = PlotRepository::create(&conn, &plot).unwrap();

        // Now manually update the plot to link it to the row
        conn.execute(
            "UPDATE plots SET row_id = ? WHERE id = ?",
            rusqlite::params![row_id_val, created_plot.id],
        ).unwrap();

        (section_id_val, square_id_val, row_id_val, created_plot.id)
    };

    // Second connection: verify hierarchical path persists and is readable with all identifiers
    {
        let conn = Connection::open(&temp_path_str).expect("Failed to reopen database");
        conn.execute("PRAGMA foreign_keys = ON", []).expect("Failed to enable foreign keys");

        // Retrieve the plot
        let retrieved = PlotRepository::get(&conn, plot_id).unwrap();

        // Verify administrative_reference persists
        assert!(retrieved.administrative_reference.is_some());

        // Verify hierarchical_path is present and complete
        assert!(retrieved.hierarchical_path.is_some(), "Hierarchical path should be present after reopen");
        let path = retrieved.hierarchical_path.unwrap();

        // Verify all identifiers are present
        assert_eq!(path.section_id, Some(section_id), "Section ID should match");
        assert_eq!(path.square_id, Some(square_id), "Square ID should match");
        assert_eq!(path.row_id, Some(row_id), "Row ID should match");

        // Verify codes and labels
        assert_eq!(path.section_code, Some("SECTION_A".to_string()), "Section code should match");
        assert_eq!(path.section_label, Some("Section A".to_string()), "Section label should match");
        assert_eq!(path.square_code, Some("GENERAL".to_string()), "Square code should match");
        assert_eq!(path.square_label, Some("General Square".to_string()), "Square label should match");
        assert_eq!(path.row_code, Some("1".to_string()), "Row code should match");
        assert_eq!(path.row_label, Some("Row 1".to_string()), "Row label should match");
    }

    // Clean up
    std::fs::remove_file(&temp_path).ok();
}
