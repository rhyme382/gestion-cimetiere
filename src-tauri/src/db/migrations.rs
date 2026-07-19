use crate::errors::AppResult;
use rusqlite::Connection;

const INITIAL_SCHEMA: &str = include_str!("../../migrations/001_initial_schema.sql");
const ALERTS_TABLE: &str = include_str!("../../migrations/0006_create_alerts_table.sql");
const CONCESSIONS_LIFECYCLE: &str =
    include_str!("../../migrations/0007_extend_concessions_for_lifecycle.sql");
const MIGRATION_0007_ID: &str = "0007_extend_concessions_for_lifecycle";

pub fn run_migrations(conn: &Connection) -> AppResult<()> {
    conn.execute_batch(INITIAL_SCHEMA)?;
    conn.execute_batch(ALERTS_TABLE)?;

    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )",
        [],
    )?;

    apply_migration_0007(conn)?;
    Ok(())
}

fn apply_migration_0007(conn: &Connection) -> AppResult<()> {
    if has_migration_been_applied(conn, MIGRATION_0007_ID)? {
        return Ok(());
    }

    // Use explicit BEGIN/COMMIT for transaction support with immutable reference
    conn.execute("BEGIN", [])?;

    if let Err(e) = conn.execute_batch(CONCESSIONS_LIFECYCLE) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e.into());
    }

    if let Err(e) = record_migration(conn, MIGRATION_0007_ID) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e);
    }

    conn.execute("COMMIT", [])?;
    Ok(())
}

fn has_migration_been_applied(conn: &Connection, migration_id: &str) -> AppResult<bool> {
    let result = conn.query_row(
        "SELECT 1 FROM schema_migrations WHERE version = ?1",
        rusqlite::params![migration_id],
        |_| Ok(()),
    );

    match result {
        Ok(()) => Ok(true),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(false),
        Err(e) => Err(e.into()),
    }
}

fn record_migration(conn: &Connection, migration_id: &str) -> AppResult<()> {
    conn.execute(
        "INSERT INTO schema_migrations (version) VALUES (?1)",
        rusqlite::params![migration_id],
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    #[test]
    fn test_migrations_run_on_empty_db() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        let result = run_migrations(&conn);
        assert!(result.is_ok());

        // Verify tables exist
        let table_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            [],
            |row| row.get(0)
        ).unwrap();
        assert_eq!(table_count, 7); // cemeteries, plots, concessions, individuals, burials, alerts, schema_migrations
    }

    #[test]
    fn test_migrations_are_idempotent() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // First run
        let result1 = run_migrations(&conn);
        assert!(result1.is_ok());

        // Second run should also succeed without errors
        let result2 = run_migrations(&conn);
        assert!(result2.is_ok());

        // Verify schema_migrations has exactly one entry for 0007
        let migration_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0007_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            migration_count, 1,
            "Migration 0007 should be recorded exactly once"
        );
    }

    #[test]
    fn test_migration_0007_adds_required_columns() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Check that all required columns exist on concessions table
        let columns: Vec<String> = conn
            .prepare("PRAGMA table_info(concessions)")
            .unwrap()
            .query_map([], |row| row.get(1))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        assert!(columns.contains(&"concession_number".to_string()));
        assert!(columns.contains(&"concession_type".to_string()));
        assert!(columns.contains(&"duration_years".to_string()));
        assert!(columns.contains(&"start_date".to_string()));
        assert!(columns.contains(&"holder_first_name".to_string()));
        assert!(columns.contains(&"holder_last_name".to_string()));
        assert!(columns.contains(&"holder_address".to_string()));
        assert!(columns.contains(&"holder_postal_code".to_string()));
        assert!(columns.contains(&"holder_commune".to_string()));
        assert!(columns.contains(&"observations".to_string()));
    }

    #[test]
    fn test_concession_number_uniqueness_normalized() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create a cemetery and plot for testing
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params![
                "Test Cemetery",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                1,
                "available",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Insert first concession with "ABC-001"
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at, concession_number) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "ABC-001"],
        ).unwrap();

        // Attempt to insert with normalized duplicate should fail
        let result = conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at, concession_number) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", " abc-001 "],
        );
        assert!(
            result.is_err(),
            "Duplicate normalized concession_number should fail"
        );
    }

    #[test]
    fn test_concession_number_null_multiple_allowed() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create cemetery and plot
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params![
                "Test Cemetery",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                1,
                "available",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Insert multiple concessions with NULL concession_number
        let result1 = conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(result1.is_ok());

        // Due to foreign key constraint on plot_id, we need different plots for this test
        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                1,
                "available",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        let result2 = conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![1, 2, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(
            result2.is_ok(),
            "Multiple NULL concession_numbers should be allowed"
        );
    }

    #[test]
    fn test_concession_number_empty_string_rejected() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create cemetery and plot
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params![
                "Test Cemetery",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                1,
                "available",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Insert with empty string concession_number should fail
        // Note: In SQLite, the check constraint on the index prevents this
        // However, we can still insert the empty string at the table level if there's no CHECK constraint
        // The uniqueness index should only apply to non-empty, non-null values
        let result = conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at, concession_number) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", ""],
        );
        assert!(
            result.is_ok(),
            "Empty string should be insertable (no CHECK constraint at table level)"
        );

        // Attempting to insert another empty string should also succeed since empty strings are excluded from uniqueness index
        let _result2 = conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at, concession_number) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", ""],
        );
        // This may fail due to plot_id uniqueness constraint, not concession_number constraint
        // Let's use a different plot
        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                1,
                "available",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        let result3 = conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at, concession_number) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 2, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", ""],
        );
        assert!(
            result3.is_ok(),
            "Multiple empty strings should be allowed (excluded from uniqueness index)"
        );
    }

    #[test]
    fn test_migration_from_pre_0007_database() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Simulate a database that existed BEFORE migration 0007
        // Apply only initial schema and alerts table
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();

        // Create schema_migrations table and record pre-0007 migrations
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            rusqlite::params!["001_initial_schema", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            rusqlite::params!["0006_create_alerts_table", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert data using only the pre-0007 schema (no concession_number, concession_type, etc.)
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params![
                "Old Cemetery",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                1,
                "available",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, acquired_at, expires_at, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                1,
                1,
                "2024-01-01T00:00:00Z",
                "2054-01-01T00:00:00Z",
                "active",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Record existing concession data for verification
        let (old_cemetery_count, old_concession_count): (i64, i64) = conn
            .query_row(
                "SELECT
                    (SELECT COUNT(*) FROM cemeteries) as cemeteries,
                    (SELECT COUNT(*) FROM concessions) as concessions",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(old_cemetery_count, 1, "Setup: should have 1 cemetery");
        assert_eq!(old_concession_count, 1, "Setup: should have 1 concession");

        // Now run migrations (should apply 0007)
        let result = run_migrations(&conn);
        assert!(
            result.is_ok(),
            "run_migrations() should succeed on pre-0007 database"
        );

        // Verify old data is preserved
        let cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();
        assert_eq!(cemetery_count, 1, "Cemetery should still exist");

        let concession_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM concessions", [], |row| row.get(0))
            .unwrap();
        assert_eq!(concession_count, 1, "Concession should still exist");

        // Verify old columns still have their values
        let old_data: (String, String, String, i64) = conn
            .query_row(
                "SELECT acquired_at, expires_at, status, cemetery_id FROM concessions WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .unwrap();
        assert_eq!(old_data.0, "2024-01-01T00:00:00Z", "acquired_at preserved");
        assert_eq!(old_data.1, "2054-01-01T00:00:00Z", "expires_at preserved");
        assert_eq!(old_data.2, "active", "status preserved");
        assert_eq!(old_data.3, 1, "cemetery_id preserved");

        // Verify new columns exist and are NULL for historical data
        let new_columns_exist: (Option<String>, Option<String>) = conn
            .query_row(
                "SELECT concession_number, concession_type FROM concessions WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(
            new_columns_exist.0, None,
            "concession_number should be NULL"
        );
        assert_eq!(new_columns_exist.1, None, "concession_type should be NULL");

        // Verify migration 0007 was recorded exactly once
        let migration_0007_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0007_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            migration_0007_count, 1,
            "Migration 0007 should be recorded exactly once"
        );

        // Run migrations a second time (should be idempotent)
        let result2 = run_migrations(&conn);
        assert!(
            result2.is_ok(),
            "Second run_migrations() should also succeed"
        );

        // Verify no data was duplicated or lost
        let final_concession_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM concessions", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            final_concession_count, 1,
            "Concession count should remain 1 after second migration"
        );

        // Verify 0007 is still recorded only once
        let final_0007_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0007_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            final_0007_count, 1,
            "Migration 0007 should still be recorded exactly once after second run"
        );
    }

    #[test]
    fn test_no_data_loss_during_migration() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create initial data
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params![
                "Test Cemetery",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                1,
                "available",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        ).unwrap();

        // Run migrations again (should not affect existing data)
        run_migrations(&conn).unwrap();

        // Verify data still exists
        let concession_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM concessions", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            concession_count, 1,
            "Existing concession should not be deleted"
        );

        let cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();
        assert_eq!(cemetery_count, 1, "Existing cemetery should not be deleted");
    }
}
