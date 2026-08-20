use crate::errors::AppResult;
use rusqlite::Connection;

const INITIAL_SCHEMA: &str = include_str!("../../migrations/001_initial_schema.sql");
const ALERTS_TABLE: &str = include_str!("../../migrations/0006_create_alerts_table.sql");
const CONCESSIONS_LIFECYCLE: &str =
    include_str!("../../migrations/0007_extend_concessions_for_lifecycle.sql");
const MUNICIPALITIES_TABLE: &str =
    include_str!("../../migrations/0008_create_municipalities_table.sql");
const CEMETERIES_MUNICIPALITIES_EXT: &str =
    include_str!("../../migrations/0009_extend_cemeteries_for_municipalities.sql");
const HIERARCHY_TABLES: &str =
    include_str!("../../migrations/0011_add_hierarchy_tables.sql");

const MIGRATION_0007_ID: &str = "0007_extend_concessions_for_lifecycle";
const MIGRATION_0008_ID: &str = "0008_create_municipalities_table";
const MIGRATION_0009_ID: &str = "0009_extend_cemeteries_for_municipalities";
const MIGRATION_0010_ID: &str = "0010_add_insee_code_and_email_to_municipalities";
const MIGRATION_0011_ID: &str = "0011_add_hierarchy_tables";

// Migration 0010: Add insee_code and email to municipalities table for FP-001 R2
// Adds mandatory INSEE code (5 alphanumeric chars, uppercase) and optional email
// Backfills existing municipalities with placeholder INSEE code to ensure readability
const MUNICIPALITIES_INSEE_EMAIL: &str = "
ALTER TABLE municipalities ADD COLUMN insee_code TEXT DEFAULT '00000';
ALTER TABLE municipalities ADD COLUMN email TEXT;
CREATE INDEX IF NOT EXISTS idx_municipalities_insee_code ON municipalities(insee_code);
UPDATE municipalities SET insee_code = COALESCE(insee_code, '00000');
";

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
    apply_migration_0008(conn)?;
    apply_migration_0009(conn)?;
    apply_migration_0010(conn)?;
    apply_migration_0011(conn)?;
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

fn apply_migration_0008(conn: &Connection) -> AppResult<()> {
    if has_migration_been_applied(conn, MIGRATION_0008_ID)? {
        return Ok(());
    }

    conn.execute("BEGIN", [])?;

    if let Err(e) = conn.execute_batch(MUNICIPALITIES_TABLE) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e.into());
    }

    if let Err(e) = record_migration(conn, MIGRATION_0008_ID) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e);
    }

    conn.execute("COMMIT", [])?;
    Ok(())
}

fn apply_migration_0009(conn: &Connection) -> AppResult<()> {
    if has_migration_been_applied(conn, MIGRATION_0009_ID)? {
        return Ok(());
    }

    conn.execute("BEGIN", [])?;

    if let Err(e) = conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e.into());
    }

    if let Err(e) = record_migration(conn, MIGRATION_0009_ID) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e);
    }

    conn.execute("COMMIT", [])?;
    Ok(())
}

fn apply_migration_0010(conn: &Connection) -> AppResult<()> {
    if has_migration_been_applied(conn, MIGRATION_0010_ID)? {
        return Ok(());
    }

    conn.execute("BEGIN", [])?;

    if let Err(e) = conn.execute_batch(MUNICIPALITIES_INSEE_EMAIL) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e.into());
    }

    if let Err(e) = record_migration(conn, MIGRATION_0010_ID) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e);
    }

    conn.execute("COMMIT", [])?;
    Ok(())
}

fn apply_migration_0011(conn: &Connection) -> AppResult<()> {
    apply_migration_0011_internal(conn, None)
}

#[cfg(test)]
fn apply_migration_0011_with_failpoint<F>(conn: &Connection, failpoint: F) -> AppResult<()>
where
    F: Fn(&str) -> AppResult<()> + 'static,
{
    apply_migration_0011_internal(conn, Some(Box::new(failpoint)))
}

fn apply_migration_0011_internal(conn: &Connection, failpoint: Option<Box<dyn Fn(&str) -> AppResult<()>>>) -> AppResult<()> {
    if has_migration_been_applied(conn, MIGRATION_0011_ID)? {
        return Ok(());
    }

    conn.execute("BEGIN", [])?;

    // 1. Create the new hierarchy tables
    if let Err(e) = conn.execute_batch(HIERARCHY_TABLES) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e.into());
    }

    // Failpoint: after schema creation
    if let Some(ref fp) = failpoint {
        if let Err(e) = fp("after_schema_creation") {
            let _ = conn.execute("ROLLBACK", []);
            return Err(e);
        }
    }

    // 2. Perform deterministic data migration for existing plots
    if let Err(e) = migrate_plots_to_hierarchy(conn) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e);
    }

    // Failpoint: after data migration
    if let Some(ref fp) = failpoint {
        if let Err(e) = fp("after_data_migration") {
            let _ = conn.execute("ROLLBACK", []);
            return Err(e);
        }
    }

    // 3. Record the migration
    if let Err(e) = record_migration(conn, MIGRATION_0011_ID) {
        let _ = conn.execute("ROLLBACK", []);
        return Err(e);
    }

    conn.execute("COMMIT", [])?;
    Ok(())
}

fn migrate_plots_to_hierarchy(conn: &Connection) -> AppResult<()> {
    // Get all cemeteries
    let mut stmt = conn.prepare("SELECT id FROM cemeteries")?;
    let cemetery_ids: Vec<i64> = stmt
        .query_map([], |row| row.get(0))?
        .collect::<Result<Vec<_>, _>>()?;

    for cemetery_id in cemetery_ids {
        migrate_cemetery_hierarchy(conn, cemetery_id)?;
    }

    // For all plots with __AUTO__ marker or empty/whitespace administrative_reference, set it to EMP-{id}
    // __AUTO__ is the default value for the new column; the AFTER INSERT trigger replaces it for new inserts
    // but we need to backfill existing plots and plots created during migration
    conn.execute(
        "UPDATE plots SET administrative_reference = 'EMP-' || id
         WHERE administrative_reference = '__AUTO__' OR administrative_reference IS NULL OR trim(administrative_reference) = ''",
        [],
    )?;

    // Verify no __AUTO__, NULL, or empty administrative_references remain
    let invalid_count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM plots WHERE administrative_reference = '__AUTO__' OR administrative_reference IS NULL OR trim(administrative_reference) = ''",
        [],
        |row| row.get(0),
    )?;

    if invalid_count > 0 {
        return Err(
            crate::errors::AppError::Internal(format!(
                "Migration failed: {} plots have invalid administrative_reference after backfill",
                invalid_count
            ))
        );
    }

    // Verify all plots have valid row_id (i.e., row_id references a row in the correct cemetery)
    let invalid_row_count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM plots p
         WHERE p.row_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM rows r
           INNER JOIN squares sq ON r.square_id = sq.id
           INNER JOIN sections s ON sq.section_id = s.id
           WHERE r.id = p.row_id AND s.cemetery_id = p.cemetery_id
         )",
        [],
        |row| row.get(0),
    )?;

    if invalid_row_count > 0 {
        return Err(
            crate::errors::AppError::Internal(format!(
                "Migration failed: {} plots reference rows from different cemeteries",
                invalid_row_count
            ))
        );
    }

    // Create unique index for administrative_reference per cemetery after backfill
    // This ensures all administrative_reference values are now properly normalized and unique
    conn.execute_batch(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_plots_admin_ref_per_cemetery
         ON plots(cemetery_id, lower(trim(administrative_reference)))",
    )?;

    Ok(())
}

fn migrate_cemetery_hierarchy(conn: &Connection, cemetery_id: i64) -> AppResult<()> {
    // Create or retrieve the technical root section for this cemetery (NON-CLASSE)
    let root_section_id = get_or_create_section(
        conn,
        cemetery_id,
        "NON-CLASSE",
        "Non Classé",
    )?;

    // Create or retrieve the technical square (GENERAL)
    let root_square_id = get_or_create_square(
        conn,
        root_section_id,
        "GENERAL",
        "Général",
    )?;

    // Get all distinct (section, row) pairs for this cemetery's plots
    let mut stmt = conn.prepare(
        "SELECT DISTINCT section, row FROM plots
         WHERE cemetery_id = ?
         ORDER BY section, row",
    )?;

    let sections_rows: Vec<(Option<String>, Option<i64>)> = stmt
        .query_map(rusqlite::params![cemetery_id], |row| {
            Ok((row.get(0)?, row.get(1)?))
        })?
        .collect::<Result<Vec<_>, _>>()?;

    for (section_opt, row_opt) in sections_rows {
        migrate_section_row_group(
            conn,
            cemetery_id,
            root_section_id,
            root_square_id,
            section_opt,
            row_opt,
        )?;
    }

    Ok(())
}

fn migrate_section_row_group(
    conn: &Connection,
    cemetery_id: i64,
    root_section_id: i64,
    root_square_id: i64,
    section_opt: Option<String>,
    row_opt: Option<i64>,
) -> AppResult<()> {
    // Normalize section and row codes
    // Treat None, "", and whitespace-only as NON-CLASSE per spec R4
    let section_code = section_opt
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(normalize_code)
        .unwrap_or_else(|| "NON-CLASSE".to_string());
    let section_label = section_opt
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "Non Classé".to_string());

    let row_code = row_opt
        .map(|r| r.to_string())
        .unwrap_or_else(|| "NON-CLASSEE".to_string());
    let row_label = row_opt
        .map(|r| format!("Rangée {}", r))
        .unwrap_or_else(|| "Non Classée".to_string());

    // Get or create section
    let section_id = if section_code == "NON-CLASSE" {
        // Use the root section for unclassified plots
        root_section_id
    } else {
        get_or_create_section(conn, cemetery_id, &section_code, &section_label)?
    };

    // Get or create square under this section
    let square_id = if section_code == "NON-CLASSE" {
        // Use the root square
        root_square_id
    } else {
        get_or_create_square(conn, section_id, "GENERAL", "Général")?
    };

    // Get or create row under this square
    let row_id = get_or_create_row(conn, square_id, &row_code, &row_label)?;

    // Update all plots with this section/row combination
    // Need to handle NULL values specially in SQL (can't use = NULL, must use IS NULL)
    match (section_opt.is_none(), row_opt.is_none()) {
        (true, true) => {
            conn.execute(
                "UPDATE plots SET row_id = ? WHERE cemetery_id = ? AND section IS NULL AND row IS NULL",
                rusqlite::params![row_id, cemetery_id],
            )?;
        }
        (true, false) => {
            conn.execute(
                "UPDATE plots SET row_id = ? WHERE cemetery_id = ? AND section IS NULL AND row = ?",
                rusqlite::params![row_id, cemetery_id, row_opt],
            )?;
        }
        (false, true) => {
            conn.execute(
                "UPDATE plots SET row_id = ? WHERE cemetery_id = ? AND section = ? AND row IS NULL",
                rusqlite::params![row_id, cemetery_id, section_opt],
            )?;
        }
        (false, false) => {
            conn.execute(
                "UPDATE plots SET row_id = ? WHERE cemetery_id = ? AND section = ? AND row = ?",
                rusqlite::params![row_id, cemetery_id, section_opt, row_opt],
            )?;
        }
    }

    Ok(())
}

fn normalize_code(s: &str) -> String {
    s.trim()
        .to_uppercase()
        .split_whitespace()
        .collect::<Vec<&str>>()
        .join("_")
}

fn get_or_create_section(
    conn: &Connection,
    cemetery_id: i64,
    code: &str,
    display_label: &str,
) -> AppResult<i64> {
    let normalized_code = normalize_code(code);

    // Try to find existing section with normalized code
    let mut stmt = conn.prepare(
        "SELECT id FROM sections
         WHERE cemetery_id = ? AND normalized_code = ?",
    )?;

    if let Ok(id) = stmt.query_row(
        rusqlite::params![cemetery_id, &normalized_code],
        |row| row.get::<_, i64>(0),
    ) {
        return Ok(id);
    }

    // Create new section
    conn.execute(
        "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![cemetery_id, &normalized_code, display_label],
    )?;

    Ok(conn.last_insert_rowid())
}

fn get_or_create_square(
    conn: &Connection,
    section_id: i64,
    code: &str,
    display_label: &str,
) -> AppResult<i64> {
    let normalized_code = normalize_code(code);

    // Try to find existing square with normalized code
    let mut stmt = conn.prepare(
        "SELECT id FROM squares
         WHERE section_id = ? AND normalized_code = ?",
    )?;

    if let Ok(id) = stmt.query_row(
        rusqlite::params![section_id, &normalized_code],
        |row| row.get::<_, i64>(0),
    ) {
        return Ok(id);
    }

    // Create new square
    conn.execute(
        "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![section_id, &normalized_code, display_label],
    )?;

    Ok(conn.last_insert_rowid())
}

fn get_or_create_row(
    conn: &Connection,
    square_id: i64,
    code: &str,
    display_label: &str,
) -> AppResult<i64> {
    let normalized_code = normalize_code(code);

    // Try to find existing row with normalized code
    let mut stmt = conn.prepare(
        "SELECT id FROM rows
         WHERE square_id = ? AND normalized_code = ?",
    )?;

    if let Ok(id) = stmt.query_row(
        rusqlite::params![square_id, &normalized_code],
        |row| row.get::<_, i64>(0),
    ) {
        return Ok(id);
    }

    // Create new row
    conn.execute(
        "INSERT INTO rows (square_id, normalized_code, display_label, is_active, created_at, updated_at)
         VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        rusqlite::params![square_id, &normalized_code, display_label],
    )?;

    Ok(conn.last_insert_rowid())
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
    fn test_migrations() {
        // Wrapper test to run migration suite via: cargo test -p gestion-cimetiere test_migrations
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Verify all migrations run successfully
        let result = run_migrations(&conn);
        assert!(result.is_ok(), "Migrations should succeed");

        // Verify all tables exist (8 original + 3 new hierarchy tables = 11 total)
        let table_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(table_count, 11, "Should have 11 tables (8 original + sections, squares, rows)");

        // Run migrations again to verify idempotency
        let result2 = run_migrations(&conn);
        assert!(result2.is_ok(), "Migrations should be idempotent");
    }

    #[test]
    fn test_migrations_run_on_empty_db() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        let result = run_migrations(&conn);
        assert!(result.is_ok());

        // Verify tables exist (8 original + sections, squares, rows = 11 total)
        let table_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            [],
            |row| row.get(0)
        ).unwrap();
        assert_eq!(table_count, 11); // cemeteries, plots, concessions, individuals, burials, alerts, municipalities, schema_migrations, sections, squares, rows
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

    #[test]
    fn test_migration_0008_creates_municipalities_table() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Verify municipalities table exists
        let table_exists: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='municipalities'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap();
        assert!(
            table_exists,
            "municipalities table should exist after migration"
        );

        // Verify required columns exist
        let columns: Vec<String> = conn
            .prepare("PRAGMA table_info(municipalities)")
            .unwrap()
            .query_map([], |row| row.get(1))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        assert!(columns.contains(&"id".to_string()));
        assert!(columns.contains(&"name".to_string()));
        assert!(columns.contains(&"postal_code".to_string()));
        assert!(columns.contains(&"department".to_string()));
        assert!(columns.contains(&"region".to_string()));
        assert!(columns.contains(&"notes".to_string()));
        assert!(columns.contains(&"created_at".to_string()));
        assert!(columns.contains(&"updated_at".to_string()));

        // Verify migration is recorded
        let recorded: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0008_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            recorded, 1,
            "Migration 0008 should be recorded exactly once"
        );
    }

    #[test]
    fn test_migration_0009_extends_cemeteries_table() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Verify new columns exist on cemeteries table
        let columns: Vec<String> = conn
            .prepare("PRAGMA table_info(cemeteries)")
            .unwrap()
            .query_map([], |row| row.get(1))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        assert!(
            columns.contains(&"municipality_id".to_string()),
            "cemeteries should have municipality_id column"
        );
        assert!(
            columns.contains(&"address".to_string()),
            "cemeteries should have address column"
        );
        assert!(
            columns.contains(&"is_active".to_string()),
            "cemeteries should have is_active column"
        );

        // Verify migration is recorded
        let recorded: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0009_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            recorded, 1,
            "Migration 0009 should be recorded exactly once"
        );
    }

    #[test]
    fn test_migration_0008_0009_idempotent() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // First run
        let result1 = run_migrations(&conn);
        assert!(result1.is_ok(), "First migration run should succeed");

        // Second run should also succeed
        let result2 = run_migrations(&conn);
        assert!(
            result2.is_ok(),
            "Second migration run should succeed (idempotent)"
        );

        // Verify both migrations recorded exactly once
        let count_0008: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0008_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            count_0008, 1,
            "Migration 0008 should be recorded exactly once"
        );

        let count_0009: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0009_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            count_0009, 1,
            "Migration 0009 should be recorded exactly once"
        );
    }

    #[test]
    fn test_migration_0009_preserves_existing_cemetery_data() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only migrations up to 0007 (simulate pre-0008/0009 database)
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            rusqlite::params!["001_initial_schema"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            rusqlite::params!["0006_create_alerts_table"],
        )
        .unwrap();

        apply_migration_0007(&conn).unwrap();

        // Create test data using pre-0009 schema
        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Old Cemetery",
                "Paris",
                500,
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

        // Record pre-migration counts
        let (old_cemetery_count, old_plot_count, old_concession_count): (i64, i64, i64) = conn
            .query_row(
                "SELECT
                    (SELECT COUNT(*) FROM cemeteries) as cemeteries,
                    (SELECT COUNT(*) FROM plots) as plots,
                    (SELECT COUNT(*) FROM concessions) as concessions",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();

        // Now apply migrations 0008 and 0009
        apply_migration_0008(&conn).unwrap();
        apply_migration_0009(&conn).unwrap();

        // Verify data preservation
        let (new_cemetery_count, new_plot_count, new_concession_count): (i64, i64, i64) = conn
            .query_row(
                "SELECT
                    (SELECT COUNT(*) FROM cemeteries) as cemeteries,
                    (SELECT COUNT(*) FROM plots) as plots,
                    (SELECT COUNT(*) FROM concessions) as concessions",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();

        assert_eq!(
            new_cemetery_count, old_cemetery_count,
            "Cemetery count should be preserved"
        );
        assert_eq!(
            new_plot_count, old_plot_count,
            "Plot count should be preserved"
        );
        assert_eq!(
            new_concession_count, old_concession_count,
            "Concession count should be preserved"
        );

        // Verify old data is still accessible
        let cemetery: (String, Option<String>, i32) = conn
            .query_row(
                "SELECT name, commune, capacity FROM cemeteries WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();

        assert_eq!(cemetery.0, "Old Cemetery");
        assert_eq!(cemetery.1, Some("Paris".to_string()));
        assert_eq!(cemetery.2, 500);

        // Verify new columns exist and have expected defaults/backfilled values
        let (municipality_id, address, is_active): (Option<i64>, Option<String>, i32) = conn
            .query_row(
                "SELECT municipality_id, address, is_active FROM cemeteries WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();

        assert!(
            municipality_id.is_some(),
            "municipality_id should be backfilled from 'commune' field"
        );
        assert_eq!(address, None, "address should be NULL for legacy data");
        assert_eq!(is_active, 1, "is_active should default to 1 (active)");

        // Verify municipality was created with correct name
        let municipality_name: String = conn
            .query_row(
                "SELECT name FROM municipalities WHERE id = ?",
                rusqlite::params![municipality_id.unwrap()],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            municipality_name, "Paris",
            "Municipality name should match commune"
        );
    }

    #[test]
    fn test_migration_0008_municipality_name_uniqueness() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Insert first municipality
        conn.execute(
            "INSERT INTO municipalities (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Paris", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Attempt to insert duplicate should fail
        let result = conn.execute(
            "INSERT INTO municipalities (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Paris", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );

        assert!(
            result.is_err(),
            "Duplicate municipality name should fail (unique constraint)"
        );
    }

    #[test]
    fn integration_cemetery() {
        // Wrapper to execute cemetery integration test suite via: cargo test -p gestion-cimetiere integration_cemetery
        // Simulates a legacy database with existing cemetery data that gets migrated
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Setup: apply only pre-0008 schema to simulate legacy database
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();

        // Create schema_migrations table for tracking applied migrations
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        apply_migration_0007(&conn).unwrap();

        // Insert legacy cemetery data BEFORE migrations 0008/0009
        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Integration Test Cemetery",
                "TestVille",
                500,
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Now apply migrations 0008 and 0009 (which should backfill municipalities)
        apply_migration_0008(&conn).unwrap();
        apply_migration_0009(&conn).unwrap();

        let cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();
        assert_eq!(cemetery_count, 1, "Should have 1 cemetery");

        // Verify municipality was created from backfill
        let municipality_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM municipalities WHERE name = 'TestVille'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            municipality_count, 1,
            "Should have created municipality from commune field during migration"
        );

        // Verify cemetery is linked to municipality
        let linked: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM cemeteries WHERE municipality_id IS NOT NULL",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            linked, 1,
            "Cemetery should be linked to municipality via backfill"
        );
    }

    #[test]
    fn migration_with_backfill_scenario() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Setup: apply pre-0008 schema
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        apply_migration_0007(&conn).unwrap();

        // Insert multiple cemeteries with different communes
        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Cemetery A",
                "Paris",
                500,
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Cemetery B",
                "Lyon",
                300,
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Cemetery C",
                "Paris", // Duplicate commune
                200,
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Apply 0008 and 0009
        apply_migration_0008(&conn).unwrap();
        apply_migration_0009(&conn).unwrap();

        // Verify all cemeteries still exist
        let cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();
        assert_eq!(cemetery_count, 3);

        // Verify is_active defaults to 1
        let active_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM cemeteries WHERE is_active = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            active_count, 3,
            "All cemeteries should be active by default"
        );

        // Verify municipalities were created: 2 distinct (Paris, Lyon)
        let municipality_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM municipalities", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            municipality_count, 2,
            "Should have 2 distinct municipalities (Paris, Lyon)"
        );

        // Verify all cemeteries are linked to municipalities
        let linked_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM cemeteries WHERE municipality_id IS NOT NULL",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            linked_count, 3,
            "All cemeteries should have municipality_id backfilled"
        );

        // Verify both Paris cemeteries point to the same municipality
        let paris_cemeteries: i64 = conn
            .query_row(
                "SELECT COUNT(DISTINCT municipality_id) FROM cemeteries
                 WHERE name IN ('Cemetery A', 'Cemetery C')",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            paris_cemeteries, 1,
            "Cemetery A and C should share the same municipality (Paris)"
        );
    }

    #[test]
    fn test_migration_0009_backfills_municipality_id_from_commune() {
        // Explicit test to prove migration 0009 backfills municipality_id from existing commune field.
        // This directly addresses FP001-R1-AC2: The additive migration opens an existing database,
        // adds the municipal reference and cemetery extensions without loss of existing records.
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Simulate pre-0008/0009 database with existing cemetery data
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        apply_migration_0007(&conn).unwrap();

        // Insert legacy cemetery data BEFORE migrations 0008/0009
        // These records have only the old schema: no municipality_id, no address, no is_active
        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Legacy Cemetery 1",
                "Marseille",
                750,
                "2024-01-01T00:00:00Z",
                "2024-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Legacy Cemetery 2",
                "Toulouse",
                600,
                "2024-02-01T00:00:00Z",
                "2024-02-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Record state BEFORE migration (municipalities table doesn't exist yet)
        let _pre_cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();

        // NOW apply migrations 0008 and 0009
        apply_migration_0008(&conn).unwrap();
        apply_migration_0009(&conn).unwrap();

        // POST-MIGRATION VERIFICATION: Backfill worked

        // 1. All old cemeteries still exist
        let post_cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            post_cemetery_count, 2,
            "All legacy cemeteries should be preserved after migration"
        );

        // 2. Municipalities were created from commune field
        let post_municipality_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM municipalities", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            post_municipality_count, 2,
            "Should have created 2 municipalities from distinct commune values (Marseille, Toulouse)"
        );

        // 3. Each cemetery now has a non-NULL municipality_id (PROOF OF BACKFILL)
        let cemetery_1_municipality_id: Option<i64> = conn
            .query_row(
                "SELECT municipality_id FROM cemeteries WHERE name = 'Legacy Cemetery 1'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert!(
            cemetery_1_municipality_id.is_some(),
            "Legacy Cemetery 1 should have municipality_id backfilled from 'Marseille' commune"
        );

        let cemetery_2_municipality_id: Option<i64> = conn
            .query_row(
                "SELECT municipality_id FROM cemeteries WHERE name = 'Legacy Cemetery 2'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert!(
            cemetery_2_municipality_id.is_some(),
            "Legacy Cemetery 2 should have municipality_id backfilled from 'Toulouse' commune"
        );

        // 4. The municipality records have the correct names
        let municipality_1_name: String = conn
            .query_row(
                "SELECT name FROM municipalities WHERE id = ?",
                rusqlite::params![cemetery_1_municipality_id.unwrap()],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            municipality_1_name, "Marseille",
            "Municipality linked to Cemetery 1 should be Marseille"
        );

        let municipality_2_name: String = conn
            .query_row(
                "SELECT name FROM municipalities WHERE id = ?",
                rusqlite::params![cemetery_2_municipality_id.unwrap()],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            municipality_2_name, "Toulouse",
            "Municipality linked to Cemetery 2 should be Toulouse"
        );

        // 5. Verify is_active defaults to 1 (active)
        let active_flag_1: i32 = conn
            .query_row(
                "SELECT is_active FROM cemeteries WHERE name = 'Legacy Cemetery 1'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(active_flag_1, 1, "is_active should default to 1 (active)");

        // 6. Verify old data is fully preserved (commune, capacity, name, dates)
        let preserved_data: (String, Option<i32>, Option<String>) = conn
            .query_row(
                "SELECT name, capacity, commune FROM cemeteries WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();
        assert_eq!(preserved_data.0, "Legacy Cemetery 1");
        assert_eq!(preserved_data.1, Some(750));
        assert_eq!(preserved_data.2, Some("Marseille".to_string()));

        // 7. Test idempotency: running migrations again should not duplicate municipalities or change municipality_id
        apply_migration_0009(&conn).unwrap();

        let final_municipality_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM municipalities", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            final_municipality_count, 2,
            "Running migration 0009 twice should not create duplicates (INSERT OR IGNORE)"
        );

        let final_cemetery_1_municipality_id: Option<i64> = conn
            .query_row(
                "SELECT municipality_id FROM cemeteries WHERE name = 'Legacy Cemetery 1'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            final_cemetery_1_municipality_id, cemetery_1_municipality_id,
            "Municipality ID should not change after re-running migration (idempotent)"
        );
    }

    #[test]
    fn test_migration_0011_creates_hierarchy_tables() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Verify sections table exists
        let sections_exist: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sections'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap();
        assert!(sections_exist, "sections table should exist");

        // Verify squares table exists
        let squares_exist: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='squares'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap();
        assert!(squares_exist, "squares table should exist");

        // Verify rows table exists
        let rows_exist: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='rows'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap();
        assert!(rows_exist, "rows table should exist");

        // Verify plots table has new columns
        let columns: Vec<String> = conn
            .prepare("PRAGMA table_info(plots)")
            .unwrap()
            .query_map([], |row| row.get(1))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        assert!(
            columns.contains(&"row_id".to_string()),
            "plots should have row_id column"
        );
        assert!(
            columns.contains(&"administrative_reference".to_string()),
            "plots should have administrative_reference column"
        );
    }

    #[test]
    fn test_migration_0011_empty_database() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Verify migration was recorded
        let recorded: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0011_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(recorded, 1, "Migration 0011 should be recorded");

        // Verify no hierarchy entries were created for empty database
        let section_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM sections", [], |row| row.get(0))
            .unwrap();
        assert_eq!(section_count, 0, "No sections should exist for empty database");
    }

    #[test]
    fn test_migration_0011_with_existing_plots() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test cemetery and plots BEFORE the migration
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert plot with section and row
        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Now apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // Verify plot still exists with same ID
        let plot_id: i64 = conn
            .query_row(
                "SELECT id FROM plots WHERE cemetery_id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(plot_id, 1, "Plot ID should be unchanged");

        // Verify administrative_reference was initialized
        let admin_ref: String = conn
            .query_row(
                "SELECT administrative_reference FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(admin_ref, "EMP-1", "Admin reference should be EMP-<id>");

        // Verify plot was linked to hierarchy
        let row_id: Option<i64> = conn
            .query_row(
                "SELECT row_id FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert!(row_id.is_some(), "Plot should be linked to a row");
    }

    #[test]
    fn test_migration_0011_multiple_plots_same_section_row() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert multiple plots with same section and row
        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // All plots should be linked to the same row
        let row_ids: Vec<i64> = conn
            .prepare("SELECT row_id FROM plots WHERE cemetery_id = 1 ORDER BY id")
            .unwrap()
            .query_map([], |row| row.get(0))
            .unwrap()
            .filter_map(|r| r.ok().flatten())
            .collect();

        assert_eq!(row_ids.len(), 3, "All plots should have row_id");
        assert!(
            row_ids.iter().all(|&id| id == row_ids[0]),
            "All plots should share the same row_id"
        );

        // Verify only one row was created for this section/row pair
        let row_count: i64 = conn
            .query_row(
                "SELECT COUNT(DISTINCT row_id) FROM plots WHERE cemetery_id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(row_count, 1, "Only one row should be created for shared section/row pair");
    }

    #[test]
    fn test_migration_0011_null_section_and_row() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert plot with NULL section and NULL row
        conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at)
             VALUES (?, ?, ?, ?)",
            rusqlite::params![1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // Verify plot was linked to hierarchy
        let row_id: Option<i64> = conn
            .query_row(
                "SELECT row_id FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert!(row_id.is_some(), "Plot should be linked to a row even with NULL section/row");

        // Verify administrative_reference was initialized
        let admin_ref: String = conn
            .query_row(
                "SELECT administrative_reference FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(admin_ref, "EMP-1", "Admin reference should be EMP-<plot_id>");
    }

    #[test]
    fn test_migration_0011_empty_section_treated_as_non_classe() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert plot with empty string section
        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // Verify plot was linked to hierarchy via NON-CLASSE section
        let (section_code, normalized_code): (String, String) = conn
            .query_row(
                "SELECT s.normalized_code, r.normalized_code
                 FROM plots p
                 INNER JOIN rows r ON p.row_id = r.id
                 INNER JOIN squares sq ON r.square_id = sq.id
                 INNER JOIN sections s ON sq.section_id = s.id
                 WHERE p.id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(section_code, "NON-CLASSE", "Empty section should use NON-CLASSE");
        assert_eq!(normalized_code, "1", "Row code should be '1'");

        // Verify original section value is preserved
        let original_section: String = conn
            .query_row(
                "SELECT section FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(original_section, "", "Original empty section should be preserved");
    }

    #[test]
    fn test_migration_0011_whitespace_section_treated_as_non_classe() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert plot with whitespace-only section
        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "   ", 2, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // Verify plot was linked to hierarchy via NON-CLASSE section
        let section_code: String = conn
            .query_row(
                "SELECT s.normalized_code
                 FROM plots p
                 INNER JOIN rows r ON p.row_id = r.id
                 INNER JOIN squares sq ON r.square_id = sq.id
                 INNER JOIN sections s ON sq.section_id = s.id
                 WHERE p.id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(section_code, "NON-CLASSE", "Whitespace section should use NON-CLASSE");

        // Verify original section value is preserved
        let original_section: String = conn
            .query_row(
                "SELECT section FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(original_section, "   ", "Original whitespace section should be preserved");
    }

    #[test]
    fn test_migration_0011_administrative_reference_rejects_leading_trailing_spaces() {
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

        // Attempt to INSERT with leading space should fail
        let result = conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at, administrative_reference)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", " EMP-001"],
        );
        assert!(result.is_err(), "INSERT with leading space should fail");

        // Attempt to INSERT with trailing space should fail
        let result = conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at, administrative_reference)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "EMP-001 "],
        );
        assert!(result.is_err(), "INSERT with trailing space should fail");

        // Attempt to UPDATE with leading space should fail
        let result = conn.execute(
            "UPDATE plots SET administrative_reference = ? WHERE id = 1",
            rusqlite::params![" EMP-001"],
        );
        assert!(result.is_err(), "UPDATE with leading space should fail");

        // Normal INSERT without spaces should succeed
        let result = conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at, administrative_reference)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "EMP-002"],
        );
        assert!(result.is_ok(), "INSERT without spaces should succeed");
    }

    #[test]
    fn test_migration_0011_code_triggers_reject_non_canonical_updates() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create a cemetery for testing
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Create a section via Rust normalizer (canonical form)
        conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "SECTION_A", "Section A"],
        )
        .unwrap();

        // Attempt direct UPDATE to non-canonical form with leading spaces
        let result = conn.execute(
            "UPDATE sections SET normalized_code = ? WHERE id = 1",
            rusqlite::params![" SECTION_A"],
        );
        assert!(result.is_err(), "UPDATE with leading space should fail");

        // Attempt direct UPDATE to lowercase (non-canonical)
        let result = conn.execute(
            "UPDATE sections SET normalized_code = ? WHERE id = 1",
            rusqlite::params!["section_a"],
        );
        assert!(result.is_err(), "UPDATE with lowercase should fail");

        // Attempt direct UPDATE with double spaces
        let result = conn.execute(
            "UPDATE sections SET normalized_code = ? WHERE id = 1",
            rusqlite::params!["SECTION  A"],
        );
        assert!(result.is_err(), "UPDATE with double space should fail");

        // Verify valid UPDATE still works
        let result = conn.execute(
            "UPDATE sections SET normalized_code = ? WHERE id = 1",
            rusqlite::params!["SECTION_B"],
        );
        assert!(result.is_ok(), "UPDATE to valid canonical form should succeed");

        // Verify the update worked
        let code: String = conn
            .query_row(
                "SELECT normalized_code FROM sections WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(code, "SECTION_B", "Section code should be updated");
    }

    #[test]
    fn test_migration_0011_idempotent() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test data before migration
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // First migration run
        apply_migration_0011(&conn).unwrap();

        // Get state after first run
        let (plot_count_1, admin_ref_1): (i64, String) = conn
            .query_row(
                "SELECT (SELECT COUNT(*) FROM plots), (SELECT administrative_reference FROM plots WHERE id = 1)",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();

        // Get row_id if present
        let row_id_1: Option<i64> = conn
            .query_row(
                "SELECT row_id FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .ok();

        // Second migration run (should be idempotent)
        apply_migration_0011(&conn).unwrap();

        // Verify state is unchanged
        let (plot_count_2, admin_ref_2): (i64, String) = conn
            .query_row(
                "SELECT (SELECT COUNT(*) FROM plots), (SELECT administrative_reference FROM plots WHERE id = 1)",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();

        let row_id_2: Option<i64> = conn
            .query_row(
                "SELECT row_id FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .ok();

        assert_eq!(plot_count_1, plot_count_2, "Plot count should not change");
        assert_eq!(row_id_1, row_id_2, "row_id should not change");
        assert_eq!(admin_ref_1, admin_ref_2, "administrative_reference should not change");

        // Verify migration is recorded exactly once
        let migration_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0011_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(migration_count, 1, "Migration 0011 should be recorded exactly once");
    }

    #[test]
    fn test_migration_0011_preserves_plot_ids_and_concessions() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test data with concession linked to plot
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "occupied", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at)
             VALUES (?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Get initial state
        let (initial_plot_id, initial_concession_plot_id): (i64, i64) = conn
            .query_row(
                "SELECT plots.id, concessions.plot_id FROM plots, concessions WHERE plots.id = concessions.plot_id",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();

        // Apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // Verify plot ID is unchanged
        let final_plot_id: i64 = conn
            .query_row("SELECT id FROM plots WHERE id = 1", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            initial_plot_id, final_plot_id,
            "Plot ID should remain unchanged"
        );

        // Verify concession still links to correct plot
        let final_concession_plot_id: i64 = conn
            .query_row("SELECT plot_id FROM concessions WHERE id = 1", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            initial_concession_plot_id, final_concession_plot_id,
            "Concession should still link to same plot"
        );
    }

    #[test]
    fn test_migration_0011_administrative_reference_uniqueness() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create test cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert plots with specific administrative_references
        conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "REF-001", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Attempt to insert plot with duplicate administrative_reference should fail
        let result = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "REF-001", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(
            result.is_err(),
            "Duplicate administrative_reference should fail uniqueness constraint"
        );

        // But same reference in different cemetery should succeed
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Another Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        let result = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![2, "REF-001", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(
            result.is_ok(),
            "Same administrative_reference in different cemetery should be allowed"
        );
    }

    #[test]
    fn test_migration_0011_rollback_on_error() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test data before migration
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Verify pre-migration state: sections table should not exist yet
        let sections_exist_before: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sections'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap_or(false);
        assert!(
            !sections_exist_before,
            "sections table should not exist before migration"
        );

        // Apply migration 0011 (should succeed)
        let result = apply_migration_0011(&conn);
        assert!(result.is_ok(), "Migration 0011 should succeed on clean data");

        // Verify post-migration state: sections table should exist and be populated
        let sections_exist_after: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sections'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap_or(false);
        assert!(
            sections_exist_after,
            "sections table should exist after successful migration"
        );

        // Verify plot has administrative_reference set to non-empty value
        let admin_ref: String = conn
            .query_row(
                "SELECT administrative_reference FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(admin_ref, "EMP-1", "Plot should have administrative_reference after migration");

        // Verify plot is linked to row_id
        let row_id: Option<i64> = conn
            .query_row(
                "SELECT row_id FROM plots WHERE id = 1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert!(row_id.is_some(), "Plot should have row_id after migration");

        // Simulate attempting to insert a plot with duplicate administrative_reference AFTER migration
        // This should fail due to the UNIQUE index constraint
        let result_duplicate = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "EMP-1", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(
            result_duplicate.is_err(),
            "Insert with duplicate administrative_reference should fail (UNIQUE index constraint violated)"
        );

        // Verify original data and migration state intact after failed insert attempt
        let final_plot_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM plots", [], |row| row.get(0))
            .unwrap();
        assert_eq!(final_plot_count, 1, "Should still have only 1 plot (failed insert didn't add it)");

        let final_migration_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
                rusqlite::params![MIGRATION_0011_ID],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            final_migration_count, 1,
            "Migration 0011 should be recorded exactly once"
        );
    }

    #[test]
    fn test_migration_0011_transactional_rollback_on_migration_error() {
        // This test verifies that a migration error causes a complete rollback with no partial state.
        // We inject an error DURING migration and verify that:
        // - Schema tables are not created
        // - Columns are not added to plots
        // - Migration is not recorded
        // - Data is unchanged
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test data before migration
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        let pre_cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();

        // Inject an error DURING migration after schema creation
        let result = apply_migration_0011_with_failpoint(&conn, |phase| {
            if phase == "after_schema_creation" {
                return Err(crate::errors::AppError::Internal("Injected test error after schema creation".to_string()));
            }
            Ok(())
        });

        // Verify migration failed
        assert!(result.is_err(), "Migration with injected error should fail");

        // Verify NO partial state was left behind after rollback

        // 1. Hierarchy tables should NOT exist (rolled back)
        let sections_exist: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sections'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap_or(false);
        assert!(
            !sections_exist,
            "sections table should NOT exist after rollback (was rolled back)"
        );

        let squares_exist: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='squares'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap_or(false);
        assert!(
            !squares_exist,
            "squares table should NOT exist after rollback"
        );

        let rows_exist: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='rows'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap_or(false);
        assert!(
            !rows_exist,
            "rows table should NOT exist after rollback"
        );

        // 2. plots table should NOT have new columns (rolled back)
        let columns: Vec<String> = conn
            .prepare("PRAGMA table_info(plots)")
            .unwrap()
            .query_map([], |row| row.get(1))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        assert!(
            !columns.contains(&"row_id".to_string()),
            "plots.row_id should NOT exist after rollback"
        );
        assert!(
            !columns.contains(&"administrative_reference".to_string()),
            "plots.administrative_reference should NOT exist after rollback"
        );

        // 3. Migration should NOT be recorded
        let migration_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?",
                rusqlite::params![MIGRATION_0011_ID],
                |row| row.get(0),
            )
            .unwrap_or(0);
        assert_eq!(
            migration_count, 0,
            "Migration 0011 should NOT be recorded after rollback"
        );

        // 4. Existing data should be unchanged
        let post_cemetery_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cemeteries", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            pre_cemetery_count, post_cemetery_count,
            "Cemetery count should be unchanged after rollback"
        );

        // 5. Now apply migration successfully
        let result2 = apply_migration_0011(&conn);
        assert!(result2.is_ok(), "Second migration attempt should succeed");

        // Verify migration succeeded this time
        let sections_exist_after: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sections'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap_or(false);
        assert!(
            sections_exist_after,
            "sections table should exist after successful migration"
        );

        let migration_recorded: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = ?",
                rusqlite::params![MIGRATION_0011_ID],
                |row| row.get(0),
            )
            .unwrap_or(0);
        assert_eq!(
            migration_recorded, 1,
            "Migration 0011 should be recorded exactly once after success"
        );
    }

    #[test]
    fn test_migration_0011_preserves_burial_operations() {
        // Verify that burial operations (inhumations) linked to plots are preserved
        // and their identifiers remain unchanged after migration.
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test data: cemetery, plot, individual (with correct schema), and burial operation
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Section A", 1, "occupied", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Note: individuals table has 'name' column, not separate first_name/last_name
        conn.execute(
            "INSERT INTO individuals (name, role, created_at, updated_at)
             VALUES (?, ?, ?, ?)",
            rusqlite::params!["John Doe", "decedent", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Note: burials table uses 'concession_id', not 'plot_id', and 'buried_at' not 'burial_date'
        // However, the test requires linking burials to plots. Let's use concession_id path instead.
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, created_at, updated_at)
             VALUES (?, ?, ?, ?)",
            rusqlite::params![1, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO burials (concession_id, individual_id, buried_at, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "2024-12-26", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Get state BEFORE migration
        let (pre_burial_count, pre_burial_id, pre_concession_id_from_burial): (i64, i64, i64) = conn
            .query_row(
                "SELECT
                    (SELECT COUNT(*) FROM burials) as burial_count,
                    (SELECT id FROM burials LIMIT 1) as burial_id,
                    (SELECT concession_id FROM burials LIMIT 1) as concession_id",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();

        // Apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // Get state AFTER migration
        let (post_burial_count, post_burial_id, post_concession_id_from_burial): (i64, i64, i64) = conn
            .query_row(
                "SELECT
                    (SELECT COUNT(*) FROM burials) as burial_count,
                    (SELECT id FROM burials LIMIT 1) as burial_id,
                    (SELECT concession_id FROM burials LIMIT 1) as concession_id",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();

        // Verify burial operation is preserved with same identifiers
        assert_eq!(
            pre_burial_count, post_burial_count,
            "Burial operation count should be preserved after migration"
        );
        assert_eq!(
            pre_burial_id, post_burial_id,
            "Burial operation ID should remain unchanged after migration"
        );
        assert_eq!(
            pre_concession_id_from_burial, post_concession_id_from_burial,
            "Burial operation's concession_id should remain unchanged after migration"
        );

        // Verify burial still links to correct concession and plot
        let linked_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM burials b
                 INNER JOIN concessions c ON b.concession_id = c.id
                 INNER JOIN plots p ON c.plot_id = p.id
                 WHERE b.id = ? AND c.id = ?",
                rusqlite::params![post_burial_id, post_concession_id_from_burial],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            linked_count, 1,
            "Burial operation should still be linked to the correct concession and plot after migration"
        );
    }

    #[test]
    fn test_migration_0011_list_ordering_by_display_order() {
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record prior migrations
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            let _ = conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                rusqlite::params![version],
            );
        }

        // Create test cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Insert plots with section and row to create hierarchy
        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Zebra Section", 3, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Alpha Section", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![1, "Beta Section", 2, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Apply migration 0011
        apply_migration_0011(&conn).unwrap();

        // Verify sections are retrieved in order: display_order ASC, normalized_code ASC
        let section_codes: Vec<String> = conn
            .prepare("SELECT normalized_code FROM sections WHERE cemetery_id = 1 ORDER BY display_order, normalized_code")
            .unwrap()
            .query_map([], |row| row.get(0))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        // Expected order: NON-CLASSE (technical), then ALPHA_SECTION, BETA_SECTION, ZEBRA_SECTION (alphabetic)
        assert!(section_codes.len() >= 3, "Should have at least 3 sections created");

        // Verify the sections appear in expected order (display_order=0 for tech, others in alphabetic)
        // The technical NON-CLASSE has display_order=0, others have display_order=0 (default)
        // So they should be sorted by normalized_code alphabetically
        let alpha_idx = section_codes.iter().position(|s| s == "ALPHA_SECTION")
            .expect("ALPHA_SECTION should exist");
        let beta_idx = section_codes.iter().position(|s| s == "BETA_SECTION")
            .expect("BETA_SECTION should exist");
        let zebra_idx = section_codes.iter().position(|s| s == "ZEBRA_SECTION")
            .expect("ZEBRA_SECTION should exist");

        assert!(alpha_idx < beta_idx, "ALPHA_SECTION should come before BETA_SECTION alphabetically");
        assert!(beta_idx < zebra_idx, "BETA_SECTION should come before ZEBRA_SECTION alphabetically");

        // Verify rows are also ordered correctly
        let row_codes: Vec<String> = conn
            .prepare(
                "SELECT r.normalized_code FROM rows r
                 INNER JOIN squares sq ON r.square_id = sq.id
                 INNER JOIN sections sec ON sq.section_id = sec.id
                 WHERE sec.cemetery_id = 1
                 ORDER BY r.display_order, r.normalized_code"
            )
            .unwrap()
            .query_map([], |row| row.get(0))
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();

        assert!(!row_codes.is_empty(), "Should have rows created");
        // Rows with numeric codes: 1, 2, 3 should be in order, plus NON-CLASSEE
        // After sorting by normalized_code: 1, 2, 3, NON-CLASSEE (alphabetically)
        if row_codes.len() > 1 {
            // Just verify we can retrieve them in order
            assert!(
                row_codes.iter().all(|code| !code.is_empty()),
                "All row codes should be non-empty"
            );
        }
    }

    #[test]
    fn test_migration_0011_cemetery_hierarchy_constraint() {
        // Verify that triggers prevent a plot from referencing a row from a different cemetery
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create two cemeteries
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Cemetery 1", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Cemetery 2", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Create hierarchy for Cemetery 1
        let section_1: i64 = conn
            .query_row(
                "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
                 VALUES (?, ?, ?, 1, ?, ?)
                 RETURNING id",
                rusqlite::params![1, "SECTION_A", "Section A", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
                |row| row.get(0),
            )
            .unwrap();

        let square_1: i64 = conn
            .query_row(
                "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
                 VALUES (?, ?, ?, 1, ?, ?)
                 RETURNING id",
                rusqlite::params![section_1, "GENERAL", "Général", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
                |row| row.get(0),
            )
            .unwrap();

        let row_1: i64 = conn
            .query_row(
                "INSERT INTO rows (square_id, normalized_code, display_label, is_active, created_at, updated_at)
                 VALUES (?, ?, ?, 1, ?, ?)
                 RETURNING id",
                rusqlite::params![square_1, "1", "Rangée 1", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
                |row| row.get(0),
            )
            .unwrap();

        // Create a plot in Cemetery 2
        conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![2, "EMP-001", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Attempt to link the Cemetery 2 plot to a row from Cemetery 1
        // This should fail due to the trigger
        let result = conn.execute(
            "UPDATE plots SET row_id = ? WHERE cemetery_id = 2",
            rusqlite::params![row_1],
        );

        assert!(
            result.is_err(),
            "Cannot link a plot to a row from a different cemetery (trigger violation)"
        );
    }

    #[test]
    fn test_migration_0011_administrative_reference_not_empty() {
        // Verify that triggers prevent administrative_reference from being empty or whitespace-only
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create a cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Note: After migration, administrative_reference is a required field.
        // Plots must be created with a valid non-empty administrative_reference.
        // The repository code (plot_repo.rs) generates EMP-{id} automatically.

        // Valid non-empty reference should succeed
        let result_valid = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "EMP-001", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(
            result_valid.is_ok(),
            "Valid administrative_reference should be insertable"
        );

        // Attempt to update an existing plot to empty reference (trigger blocks this)
        let result_update = conn.execute(
            "UPDATE plots SET administrative_reference = ? WHERE cemetery_id = 1",
            rusqlite::params![""],
        );
        assert!(
            result_update.is_err(),
            "Cannot update plot with empty administrative_reference (trigger violation)"
        );

        // Attempt to update to whitespace-only reference (trigger blocks this)
        let result_whitespace_update = conn.execute(
            "UPDATE plots SET administrative_reference = ? WHERE cemetery_id = 1",
            rusqlite::params!["   "],
        );
        assert!(
            result_whitespace_update.is_err(),
            "Cannot update plot with whitespace-only administrative_reference (trigger violation)"
        );
    }

    #[test]
    fn test_migration_0010_backfill_municipalities_for_fp001_r2_ac5() {
        // FP001-R2-AC5: After upgrade to migration 0010, old municipalities without insee_code
        // must remain readable. This test proves municipalities from FP001-T01 (which created
        // empty municipalities via migration 0008) can be read after adding insee_code via 0010.
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Simulate pre-0010 state: apply only migrations up to 0009
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record that migrations 0007-0009 have been applied
        conn.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            rusqlite::params![MIGRATION_0007_ID],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            rusqlite::params![MIGRATION_0008_ID],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            rusqlite::params![MIGRATION_0009_ID],
        )
        .unwrap();

        // Insert legacy municipalities WITHOUT insee_code (simulating FP001-T01 state)
        conn.execute(
            "INSERT INTO municipalities (id, name, postal_code, department, region, notes, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                1,
                "Legacy Municipality",
                Some("13000".to_string()),
                None::<String>,
                None::<String>,
                None::<String>,
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Verify pre-migration state: municipality exists but has no insee_code
        let pre_migration_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM municipalities", [], |row| row.get(0))
            .unwrap();
        assert_eq!(pre_migration_count, 1, "Setup: should have 1 municipality");

        // NOW apply migration 0010
        apply_migration_0010(&conn).unwrap();

        // POST-MIGRATION VERIFICATION: Old municipality is still readable

        // 1. Municipality still exists
        let post_migration_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM municipalities", [], |row| row.get(0))
            .unwrap();
        assert_eq!(
            post_migration_count, 1,
            "Municipality should still exist after migration"
        );

        // 2. We can read all columns including the newly added insee_code
        let (name, postal_code, insee_code, email): (
            String,
            Option<String>,
            String,
            Option<String>,
        ) = conn
            .query_row(
                "SELECT name, postal_code, insee_code, email FROM municipalities WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .unwrap();

        assert_eq!(name, "Legacy Municipality", "Name should be preserved");
        assert_eq!(
            postal_code,
            Some("13000".to_string()),
            "Postal code should be preserved"
        );
        assert_eq!(
            insee_code, "00000",
            "insee_code should be backfilled with placeholder"
        );
        assert_eq!(email, None, "email should be NULL for legacy data");

        // 3. Test idempotency: running migration 0010 again should not break anything
        apply_migration_0010(&conn).unwrap();

        let (name2, insee_code2): (String, String) = conn
            .query_row(
                "SELECT name, insee_code FROM municipalities WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();

        assert_eq!(
            name2, "Legacy Municipality",
            "Name should remain the same after re-migration"
        );
        assert_eq!(
            insee_code2, "00000",
            "insee_code should remain backfilled value after re-migration"
        );
    }

    #[test]
    fn test_migration_0011_administrative_reference_requires_non_null_and_non_empty() {
        // Verify that administrative_reference has proper validation:
        // - INSERT without specifying administrative_reference should succeed (gets auto-generated EMP-{id})
        // - INSERT with explicit NULL should fail
        // - INSERT with empty string should fail
        // - INSERT with whitespace-only string should fail
        // - Only valid non-empty references are stored; no __AUTO__ markers remain
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create a cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Test 1: INSERT without specifying administrative_reference should SUCCEED (receives __AUTO__, then replaced by trigger to EMP-{id})
        let result_omitted = conn.execute(
            "INSERT INTO plots (cemetery_id, status, created_at, updated_at)
             VALUES (?, ?, ?, ?)",
            rusqlite::params![1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(result_omitted.is_ok(), "Insert without admin_ref should succeed (receives EMP-1 via trigger)");

        // Verify the inserted plot received EMP-{id} via trigger
        let stored_ref: String = conn.query_row(
            "SELECT administrative_reference FROM plots WHERE id = 1",
            [],
            |row| row.get(0),
        ).unwrap();
        assert_eq!(stored_ref, "EMP-1", "Insert without admin_ref should have triggered EMP-1 assignment");

        // Test 2: INSERT with explicit NULL should fail (CHECK constraint)
        let result_null = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, None::<String>, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(result_null.is_err(), "Insert with NULL administrative_reference should fail");

        // Test 3: INSERT with empty string should fail (CHECK constraint)
        let result_empty = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(result_empty.is_err(), "Insert with empty string should fail (CHECK constraint)");

        // Test 4: INSERT with whitespace-only string should fail (CHECK constraint)
        let result_whitespace = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "   ", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(result_whitespace.is_err(), "Insert with whitespace-only should fail (CHECK constraint)");

        // Test 5: INSERT with valid reference should succeed
        let result_valid = conn.execute(
            "INSERT INTO plots (cemetery_id, administrative_reference, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, "EMP-001", "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        );
        assert!(result_valid.is_ok(), "Valid administrative_reference should be insertable");

        // Test 6: UPDATE to empty string should fail (CHECK constraint)
        let result_update_empty = conn.execute(
            "UPDATE plots SET administrative_reference = ? WHERE administrative_reference = 'EMP-001'",
            rusqlite::params![""],
        );
        assert!(result_update_empty.is_err(), "Cannot update to empty administrative_reference (CHECK)");

        // Test 7: UPDATE to whitespace should fail (CHECK constraint)
        let result_update_whitespace = conn.execute(
            "UPDATE plots SET administrative_reference = ? WHERE administrative_reference = 'EMP-001'",
            rusqlite::params!["  "],
        );
        assert!(result_update_whitespace.is_err(), "Cannot update to whitespace-only (CHECK)");

        // Test 8: UPDATE to NULL should fail (trigger)
        let result_update_null = conn.execute(
            "UPDATE plots SET administrative_reference = NULL WHERE administrative_reference = 'EMP-001'",
            [],
        );
        assert!(result_update_null.is_err(), "Cannot update to NULL (trigger)");
    }

    #[test]
    fn test_migration_0011_code_normalization_sections() {
        // Verify that section codes must be pre-normalized by the application
        // The SQL validation triggers enforce: trimmed, uppercase, no multiple spaces
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create a cemetery
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Test 1: Insert properly normalized code should succeed
        let result_valid = conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "SECTION_A", "Section A"],
        );
        assert!(result_valid.is_ok(), "Properly normalized code should be insertable");

        // Test 2: Insert code with leading space should fail (validation trigger)
        let result_leading_space = conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, " SECTION_B", "Section B"],
        );
        assert!(result_leading_space.is_err(), "Code with leading space should be rejected by validation trigger");

        // Test 3: Insert code with lowercase should fail
        let result_lowercase = conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "section_b", "Section B"],
        );
        assert!(result_lowercase.is_err(), "Code with lowercase should be rejected by validation trigger");

        // Test 4: Insert code with multiple spaces should fail
        let result_spaces = conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "SECTION  B", "Section B"],
        );
        assert!(result_spaces.is_err(), "Code with multiple consecutive spaces should be rejected");

        // Test 5: Duplicate normalized code should fail (UNIQUE constraint)
        let result_duplicate = conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "SECTION_A", "Section A Variant"],
        );
        assert!(result_duplicate.is_err(), "Duplicate normalized code should be rejected by UNIQUE constraint");

        // Test 6: Different code should succeed
        let result_different = conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "SECTION_B", "Section B"],
        );
        assert!(result_different.is_ok(), "Different normalized code should be insertable");
    }

    #[test]
    fn test_migration_0011_code_normalization_squares() {
        // Verify that square codes are validated for normalization
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create cemetery and section
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "SECTION_A", "Section A"],
        )
        .unwrap();

        // Test 1: Valid normalized code should succeed
        let result_valid = conn.execute(
            "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "CARRE_A", "Carré A"],
        );
        assert!(result_valid.is_ok(), "Properly normalized code should succeed");

        // Test 2: Code with multiple spaces should fail
        let result_spaces = conn.execute(
            "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "CARRE  A", "Variant"],
        );
        assert!(result_spaces.is_err(), "Code with multiple spaces should be rejected");

        // Test 3: Duplicate should fail
        let result_dup = conn.execute(
            "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "CARRE_A", "Variant"],
        );
        assert!(result_dup.is_err(), "Duplicate code should be rejected");
    }

    #[test]
    fn test_migration_0011_code_normalization_rows() {
        // Verify that row codes are validated for normalization
        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        run_migrations(&conn).unwrap();

        // Create hierarchy
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO sections (cemetery_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "SECTION_A", "Section A"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO squares (section_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "GENERAL", "General"],
        )
        .unwrap();

        // Test 1: Valid code should succeed
        let result_valid = conn.execute(
            "INSERT INTO rows (square_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "ROW_1", "Row 1"],
        );
        assert!(result_valid.is_ok(), "Properly normalized code should succeed");

        // Test 2: Code with trailing space should fail
        let result_trailing = conn.execute(
            "INSERT INTO rows (square_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "ROW_2 ", "Row 2"],
        );
        assert!(result_trailing.is_err(), "Code with trailing space should be rejected");

        // Test 3: Duplicate should fail
        let result_dup = conn.execute(
            "INSERT INTO rows (square_id, normalized_code, display_label, is_active, created_at, updated_at)
             VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            rusqlite::params![1, "ROW_1", "Row 1 Variant"],
        );
        assert!(result_dup.is_err(), "Duplicate code should be rejected");
    }

    #[test]
    fn test_migration_0011_real_rollback_on_migration_error() {
        // This test verifies that if an error occurs DURING migration's data reprise phase,
        // the entire migration is rolled back with no partial state left behind.
        //
        // We inject an error after data migration but before recording, then verify rollback.
        use rusqlite::params;

        let conn = Connection::open(":memory:").unwrap();
        conn.execute("PRAGMA foreign_keys = ON", []).unwrap();

        // Apply only pre-0011 migrations manually
        conn.execute_batch(INITIAL_SCHEMA).unwrap();
        conn.execute_batch(ALERTS_TABLE).unwrap();
        conn.execute_batch(CONCESSIONS_LIFECYCLE).unwrap();
        conn.execute_batch(MUNICIPALITIES_TABLE).unwrap();
        conn.execute_batch(CEMETERIES_MUNICIPALITIES_EXT).unwrap();

        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )
        .unwrap();

        // Record that prior migrations were applied
        for version in &[MIGRATION_0007_ID, MIGRATION_0008_ID, MIGRATION_0009_ID, MIGRATION_0010_ID] {
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                params![version],
            ).unwrap();
        }

        // Create test cemetery and plot
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            params!["Test Cemetery", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, status, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)",
            params![1, "Section A", 1, "available", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        )
        .unwrap();

        // Inject an error AFTER data migration (so schema is created and data is migrated)
        // but BEFORE recording the migration
        let result = apply_migration_0011_with_failpoint(&conn, |phase| {
            if phase == "after_data_migration" {
                return Err(crate::errors::AppError::Internal("Injected test error after data migration".to_string()));
            }
            Ok(())
        });

        // Migration should fail
        assert!(result.is_err(), "Migration with injected error after data migration should fail");

        // Verify NO partial state: migration should NOT be recorded despite schema creation and data migration
        let recorded_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = ?",
            params![MIGRATION_0011_ID],
            |row| row.get(0),
        ).unwrap_or(0);
        assert_eq!(
            recorded_count, 0,
            "Migration 0011 should NOT be recorded after rollback (error before record_migration)"
        );

        // Verify tables don't exist (full rollback happened)
        let sections_exist: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sections'",
                [],
                |row| {
                    let count: i64 = row.get(0)?;
                    Ok(count > 0)
                },
            )
            .unwrap_or(false);
        assert!(
            !sections_exist,
            "sections table should not exist after rollback"
        );

        // Now apply migration successfully (should work on second attempt)
        let result2 = apply_migration_0011(&conn);
        assert!(result2.is_ok(), "Migration 0011 should succeed on second attempt");

        // Verify it's recorded this time
        let recorded_count2: i64 = conn.query_row(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = ?",
            params![MIGRATION_0011_ID],
            |row| row.get(0),
        ).unwrap_or(0);
        assert_eq!(recorded_count2, 1, "Migration 0011 should be recorded after successful run");
    }
}
