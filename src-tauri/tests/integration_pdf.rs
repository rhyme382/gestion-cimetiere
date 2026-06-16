use rusqlite::Connection;

fn setup_test_db() -> Connection {
    let conn = Connection::open_in_memory().unwrap();

    let migrations = vec![
        include_str!("../migrations/001_initial_schema.sql"),
        include_str!("../migrations/0006_create_alerts_table.sql"),
    ];

    for migration in migrations {
        conn.execute_batch(migration).unwrap();
    }

    conn
}

#[test]
fn test_integration_pdf_generation_basic() {
    let conn = setup_test_db();

    // Setup: create cemetery and plot
    conn.execute(
        "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
        rusqlite::params!["Test Cemetery", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO plots (cemetery_id, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 10, "available", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO concessions (cemetery_id, plot_id, status, expires_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        rusqlite::params![1, 1, "active", "2027-06-16", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    // Verify concession was created
    let concession_count: i64 = conn
        .query_row("SELECT COUNT(*) FROM concessions", [], |row| row.get(0))
        .unwrap();

    assert_eq!(concession_count, 1);
}

#[test]
fn test_integration_pdf_with_burials() {
    let conn = setup_test_db();

    // Setup: create cemetery, plot, concession, and burial
    conn.execute(
        "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
        rusqlite::params!["Test Cemetery", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO plots (cemetery_id, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 10, "available", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO concessions (cemetery_id, plot_id, status, expires_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        rusqlite::params![1, 1, "active", "2027-06-16", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO individuals (name, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
        rusqlite::params!["John Doe", "beneficiary", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO burials (concession_id, individual_id, buried_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 1, "2026-06-10", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    // Verify burial was created
    let burial_count: i64 = conn
        .query_row("SELECT COUNT(*) FROM burials", [], |row| row.get(0))
        .unwrap();

    assert_eq!(burial_count, 1);
}

#[test]
fn test_integration_pdf_with_multiple_burials() {
    let conn = setup_test_db();

    // Setup
    conn.execute(
        "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
        rusqlite::params!["Test Cemetery", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO plots (cemetery_id, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 10, "available", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO concessions (cemetery_id, plot_id, status, expires_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        rusqlite::params![1, 1, "active", "2027-06-16", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    // Add multiple individuals
    for i in 1..=3 {
        conn.execute(
            "INSERT INTO individuals (name, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                format!("Deceased {}", i),
                "deceased",
                "2026-06-16 10:00:00",
                "2026-06-16 10:00:00"
            ],
        ).unwrap();
    }

    // Add multiple burials
    for i in 1..=3 {
        conn.execute(
            "INSERT INTO burials (concession_id, individual_id, buried_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, i, "2026-06-10", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();
    }

    // Verify all burials were created
    let burial_count: i64 = conn
        .query_row("SELECT COUNT(*) FROM burials", [], |row| row.get(0))
        .unwrap();

    assert_eq!(burial_count, 3);
}
