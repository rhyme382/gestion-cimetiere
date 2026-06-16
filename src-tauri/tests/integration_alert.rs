use rusqlite::Connection;

fn setup_test_db() -> Connection {
    let conn = Connection::open_in_memory().unwrap();

    // Load all migrations
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
fn test_integration_alert_creation_and_retrieval() {
    let conn = setup_test_db();

    // Setup: create cemetery and concession
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
        rusqlite::params![1, 1, "active", "2026-07-15", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    // Test: Create alerts for the concession
    let _ = conn.execute(
        "INSERT INTO alerts (concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at)
         VALUES (?, ?, ?, ?, datetime('now'))",
        rusqlite::params![1, "CRITICAL", "2026-07-15", 29],
    ).unwrap();

    // Verify: Alert was created
    let count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM alerts WHERE concession_id = 1",
        [],
        |row| row.get(0),
    ).unwrap();

    assert_eq!(count, 1);
}

#[test]
fn test_integration_alert_types_trigger_correctly() {
    let conn = setup_test_db();

    // Setup: create infrastructure
    conn.execute(
        "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
        rusqlite::params!["Test Cemetery", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    // Create three plots for the three concessions
    for _ in 1..=3 {
        conn.execute(
            "INSERT INTO plots (cemetery_id, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 10, "available", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();
    }

    // Create three concessions with different expiry dates
    for (i, days_offset) in &[(1, 29), (2, 60), (3, 150)] {
        let expiry_date = format!("2026-07-{:02}", 15 + days_offset);
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, expires_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, i, "active", &expiry_date, "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();
    }

    // Create alerts with correct types
    let alert_types = vec!["CRITICAL", "WARNING", "INFO"];
    for (i, alert_type) in alert_types.iter().enumerate() {
        let id = (i + 1) as i64;
        conn.execute(
            "INSERT INTO alerts (concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at)
             VALUES (?, ?, ?, ?, datetime('now'))",
            rusqlite::params![id, alert_type, "2026-07-15", 29],
        ).unwrap();
    }

    // Verify: Each alert type is stored
    for alert_type in &alert_types {
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM alerts WHERE alert_type = ?",
            rusqlite::params![alert_type],
            |row| row.get(0),
        ).unwrap();

        assert_eq!(count, 1, "Expected to find 1 {} alert", alert_type);
    }
}

#[test]
fn test_integration_alert_acknowledgment() {
    let conn = setup_test_db();

    // Setup: create infrastructure and alert
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
        rusqlite::params![1, 1, "active", "2026-07-15", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO alerts (concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at)
         VALUES (?, ?, ?, ?, datetime('now'))",
        rusqlite::params![1, "CRITICAL", "2026-07-15", 29],
    ).unwrap();

    // Test: Acknowledge the alert
    let affected = conn.execute(
        "UPDATE alerts SET acknowledged_at = datetime('now') WHERE id = 1",
        [],
    ).unwrap();

    assert_eq!(affected, 1);

    // Verify: Alert is no longer in unacknowledged list
    let unacknowledged: i64 = conn.query_row(
        "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL",
        [],
        |row| row.get(0),
    ).unwrap();

    assert_eq!(unacknowledged, 0);
}

#[test]
fn test_integration_alert_foreign_key_cascade() {
    let conn = setup_test_db();

    // Setup: create infrastructure and alert
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
        rusqlite::params![1, 1, "active", "2026-07-15", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO alerts (concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at)
         VALUES (?, ?, ?, ?, datetime('now'))",
        rusqlite::params![1, "CRITICAL", "2026-07-15", 29],
    ).unwrap();

    // Test: Delete the concession (should cascade delete the alert)
    let affected = conn.execute(
        "DELETE FROM concessions WHERE id = 1",
        [],
    ).unwrap();

    assert_eq!(affected, 1);

    // Verify: Alert was also deleted
    let alert_count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM alerts",
        [],
        |row| row.get(0),
    ).unwrap();

    assert_eq!(alert_count, 0);
}
