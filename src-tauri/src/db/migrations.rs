use rusqlite::Connection;
use crate::errors::AppResult;

const INITIAL_SCHEMA: &str = include_str!("../../migrations/001_initial_schema.sql");
const ALERTS_TABLE: &str = include_str!("../../migrations/0006_create_alerts_table.sql");

pub fn run_migrations(conn: &Connection) -> AppResult<()> {
    // For MVP, we'll run the schema directly
    // In a production system, we'd use a migration versioning table
    conn.execute_batch(INITIAL_SCHEMA)?;
    conn.execute_batch(ALERTS_TABLE)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    #[test]
    fn test_migrations_run() {
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
        assert_eq!(table_count, 6); // cemeteries, plots, concessions, individuals, burials, alerts
    }
}
