use gestion_cimetiere::core::models::{Cemetery, Concession, Plot};
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{CemeteryRepository, ConcessionRepository, PlotRepository};
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

#[test]
fn test_plot_id_stability_with_concession_operations() {
    let conn = setup_db();

    // Create cemetery and plot
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
    let original_plot_id = created_plot.id;

    // Create a concession for the plot
    let mut concession = Concession::new(created_cemetery.id, Some(original_plot_id));
    concession.concession_number = Some("CON-001".to_string());
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(30);
    concession.start_date = Some("2024-01-01".to_string());

    let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();
    assert_eq!(created_concession.plot_id, Some(original_plot_id));

    // Update the plot (change capacity)
    let mut updated_plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        2, // Changed capacity
    );
    updated_plot.id = original_plot_id;
    PlotRepository::update(&conn, original_plot_id, &updated_plot).unwrap();

    // Verify plot_id hasn't changed
    let retrieved_plot = PlotRepository::get(&conn, original_plot_id).unwrap();
    assert_eq!(retrieved_plot.id, original_plot_id);
    assert_eq!(retrieved_plot.capacity, 2);

    // Verify concession still references the same plot_id
    let retrieved_concession = ConcessionRepository::get(&conn, created_concession.id).unwrap();
    assert_eq!(retrieved_concession.plot_id, Some(original_plot_id));
}

#[test]
fn test_administrative_reference_uniqueness_enforcement() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create first plot
    let plot1 = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        1,
    );
    let created_plot1 = PlotRepository::create(&conn, &plot1).unwrap();
    let admin_ref1 = created_plot1.administrative_reference.clone();

    // Create second plot
    let plot2 = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(2),
        1,
    );
    let created_plot2 = PlotRepository::create(&conn, &plot2).unwrap();
    let admin_ref2 = created_plot2.administrative_reference.clone();

    // Verify both have different administrative_reference (based on ID)
    assert_ne!(admin_ref1, admin_ref2);

    // Verify format is correct
    assert!(admin_ref1.is_some());
    assert!(admin_ref2.is_some());
    assert!(admin_ref1.as_ref().unwrap().starts_with("EMP-"));
    assert!(admin_ref2.as_ref().unwrap().starts_with("EMP-"));
}

#[test]
fn test_normalized_code_uniqueness_per_hierarchy_level() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create section A
    conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![created_cemetery.id, "A", "Section A"],
    ).unwrap();

    let section_id: i64 = conn.query_row(
        "SELECT id FROM sections WHERE normalized_code = ? AND cemetery_id = ?",
        rusqlite::params!["A", created_cemetery.id],
        |row| row.get(0)
    ).unwrap();

    // Create square 001 under section A
    conn.execute(
        "INSERT INTO squares (section_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![section_id, "001", "Square 001"],
    ).unwrap();

    let square_id: i64 = conn.query_row(
        "SELECT id FROM squares WHERE section_id = ? AND normalized_code = ?",
        rusqlite::params![section_id, "001"],
        |row| row.get(0)
    ).unwrap();

    // Create row 1 under square 001
    conn.execute(
        "INSERT INTO rows (square_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![square_id, "1", "Row 1"],
    ).unwrap();

    // Try to create another row with same code under same square (should fail)
    let result = conn.execute(
        "INSERT INTO rows (square_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![square_id, "1", "Another Row 1"],
    );

    assert!(result.is_err(), "Should not allow duplicate row code under same square");

    // But we CAN create row 1 under a different square (should succeed)
    conn.execute(
        "INSERT INTO squares (section_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![section_id, "002", "Square 002"],
    ).unwrap();

    let square_id2: i64 = conn.query_row(
        "SELECT id FROM squares WHERE section_id = ? AND normalized_code = ?",
        rusqlite::params![section_id, "002"],
        |row| row.get(0)
    ).unwrap();

    let result = conn.execute(
        "INSERT INTO rows (square_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![square_id2, "1", "Row 1 in Square 002"],
    );

    assert!(result.is_ok(), "Should allow same row code in different squares");
}

#[test]
fn test_plot_with_multiple_hierarchy_levels() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(100),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create hierarchy: Section A -> Square 001 -> Row 1
    let section_id: i64 = conn.query_row(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![created_cemetery.id, "A", "Section A"],
        |row| row.get(0)
    ).unwrap();

    let square_id: i64 = conn.query_row(
        "INSERT INTO squares (section_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![section_id, "001", "Square 001"],
        |row| row.get(0)
    ).unwrap();

    let row_id: i64 = conn.query_row(
        "INSERT INTO rows (square_id, normalized_code, display_label, display_order, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
        rusqlite::params![square_id, "1", "Row 1"],
        |row| row.get(0)
    ).unwrap();

    // Create multiple plots under the same row
    for i in 1..=5 {
        let plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(i),
            1,
        );
        let created_plot = PlotRepository::create(&conn, &plot).unwrap();

        // Link to the row
        conn.execute(
            "UPDATE plots SET row_id = ? WHERE id = ?",
            rusqlite::params![row_id, created_plot.id],
        ).unwrap();

        // Verify hierarchical_path is populated
        let retrieved = PlotRepository::get(&conn, created_plot.id).unwrap();
        assert!(retrieved.hierarchical_path.is_some());
        let path = retrieved.hierarchical_path.unwrap();
        assert_eq!(path.section_id, Some(section_id));
        assert_eq!(path.square_id, Some(square_id));
        assert_eq!(path.row_id, Some(row_id));
    }

    // Verify all plots have different administrative_reference
    let list = PlotRepository::list(&conn, created_cemetery.id).unwrap();
    assert_eq!(list.len(), 5);

    let admin_refs: Vec<_> = list
        .iter()
        .map(|p| p.administrative_reference.clone())
        .collect();

    // Check uniqueness
    let mut unique_refs = admin_refs.clone();
    unique_refs.sort();
    unique_refs.dedup();
    assert_eq!(unique_refs.len(), admin_refs.len(), "All administrative_references should be unique");
}

#[test]
fn test_plot_id_persistence_across_hierarchy_updates() {
    let temp_dir = std::env::temp_dir();
    let temp_path = temp_dir.join("test_plot_id_hierarchy_persistence.db");
    let temp_path_str = temp_path.to_string_lossy().to_string();

    std::fs::remove_file(&temp_path).ok();

    let plot_id = {
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
            Some(1),
            1,
        );
        let created_plot = PlotRepository::create(&conn, &plot).unwrap();
        created_plot.id
    };

    // Close connection and reopen
    {
        let conn = Connection::open(&temp_path_str).expect("Failed to reopen database");
        conn.execute("PRAGMA foreign_keys = ON", []).expect("Failed to enable foreign keys");

        let retrieved = PlotRepository::get(&conn, plot_id).unwrap();
        assert_eq!(retrieved.id, plot_id, "Plot ID should persist exactly");
    }

    std::fs::remove_file(&temp_path).ok();
}

#[test]
fn test_administrative_reference_persistence_and_format() {
    let temp_dir = std::env::temp_dir();
    let temp_path = temp_dir.join("test_admin_ref_format.db");
    let temp_path_str = temp_path.to_string_lossy().to_string();

    std::fs::remove_file(&temp_path).ok();

    let (plot_id, expected_admin_ref) = {
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
            Some(1),
            1,
        );
        let created_plot = PlotRepository::create(&conn, &plot).unwrap();
        (
            created_plot.id,
            created_plot.administrative_reference.clone().unwrap(),
        )
    };

    // Verify format and persistence
    {
        let conn = Connection::open(&temp_path_str).expect("Failed to reopen database");
        conn.execute("PRAGMA foreign_keys = ON", []).expect("Failed to enable foreign keys");

        let retrieved = PlotRepository::get(&conn, plot_id).unwrap();
        assert_eq!(
            retrieved.administrative_reference.as_ref().map(|s| s.as_str()),
            Some(expected_admin_ref.as_str()),
            "Administrative reference should persist with exact format"
        );
        assert_eq!(
            retrieved.administrative_reference.as_ref().unwrap(),
            &format!("EMP-{}", plot_id),
            "Administrative reference should follow EMP-{{id}} format"
        );
    }

    std::fs::remove_file(&temp_path).ok();
}

#[test]
fn test_plot_id_stability_with_capacity_updates() {
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
    let original_id = created_plot.id;

    // Update capacity multiple times
    for new_capacity in 2..10 {
        let mut updated_plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(1),
            new_capacity,
        );
        updated_plot.id = original_id;
        let result = PlotRepository::update(&conn, original_id, &updated_plot).unwrap();

        assert_eq!(result.id, original_id, "Plot ID should never change on update");
        assert_eq!(result.capacity, new_capacity);
    }

    // Verify plot_id is still the same in database
    let final_plot = PlotRepository::get(&conn, original_id).unwrap();
    assert_eq!(final_plot.id, original_id);
    assert_eq!(final_plot.capacity, 9);
}
