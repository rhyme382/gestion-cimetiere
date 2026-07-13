use crate::db::DbConnection;
use crate::dto::DiagnosticDTO;
use tauri::State;

const APP_VERSION: &str = env!("CARGO_PKG_VERSION");

fn check_sqlite_health(conn: &std::sync::MutexGuard<rusqlite::Connection>) -> bool {
    conn.query_row("PRAGMA user_version", [], |_row| Ok(()))
        .is_ok()
}

fn build_diagnostic_result(
    version: String,
    health_check_passed: bool,
    error_details: Option<String>,
) -> DiagnosticDTO {
    if health_check_passed {
        DiagnosticDTO::healthy(version)
    } else {
        let error_msg = error_details.unwrap_or_else(|| "SQLite health check failed".to_string());
        DiagnosticDTO::sqlite_error(version, error_msg)
    }
}

#[tauri::command]
pub fn get_diagnostic(state: State<DbConnection>) -> DiagnosticDTO {
    match state.lock() {
        Ok(conn) => {
            let health_ok = check_sqlite_health(&conn);
            build_diagnostic_result(APP_VERSION.to_string(), health_ok, None)
        }
        Err(e) => build_diagnostic_result(
            APP_VERSION.to_string(),
            false,
            Some(format!("Failed to acquire database lock: {}", e)),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::init_db;

    #[test]
    fn test_diagnostic_healthy_with_in_memory_db() {
        let db_conn = init_db(":memory:").expect("Failed to initialize in-memory database");
        let conn = db_conn.lock().expect("Failed to lock connection");
        let is_healthy = check_sqlite_health(&conn);

        assert!(is_healthy);
    }

    #[test]
    fn test_diagnostic_with_temp_file_db() {
        let temp_dir = tempfile::tempdir().expect("Failed to create temp directory");
        let db_path = temp_dir.path().join("test.db");

        let db_conn =
            init_db(db_path.to_str().unwrap()).expect("Failed to initialize temp file database");
        let conn = db_conn.lock().expect("Failed to lock connection");
        let is_healthy = check_sqlite_health(&conn);

        assert!(
            is_healthy,
            "Database health check should succeed with valid DB"
        );
    }

    #[test]
    fn test_diagnostic_sqlite_error_behavior() {
        let temp_dir = tempfile::tempdir().expect("Failed to create temp directory");
        let db_path = temp_dir.path().join("test.db");

        let db_conn = init_db(db_path.to_str().unwrap()).expect("Failed to initialize database");
        {
            let conn = db_conn.lock().expect("Failed to lock connection");
            assert!(
                check_sqlite_health(&conn),
                "Initial health check should pass"
            );
        }

        #[cfg(unix)]
        {
            use std::fs;
            use std::os::unix::fs::PermissionsExt;

            drop(db_conn);

            let perms = fs::Permissions::from_mode(0o000);
            fs::set_permissions(temp_dir.path(), perms).expect("Failed to remove read permissions");

            let db_conn_result = init_db(db_path.to_str().unwrap());
            assert!(
                db_conn_result.is_err(),
                "Should fail to open DB with no permissions"
            );

            let perms = fs::Permissions::from_mode(0o755);
            fs::set_permissions(temp_dir.path(), perms).expect("Failed to restore permissions");
        }
    }

    #[test]
    fn test_diagnostic_sqlite_error_message_structure() {
        let diagnostic = DiagnosticDTO::sqlite_error(
            "0.1.0".to_string(),
            "Database locked or inaccessible".to_string(),
        );

        assert_eq!(diagnostic.health, "degraded");
        assert!(!diagnostic.sqlite_available);
        assert_eq!(diagnostic.app_version, "0.1.0");
        assert!(
            diagnostic
                .message
                .contains("SQLite connection check failed"),
            "Error message should be properly structured"
        );
        assert!(
            diagnostic.message.contains("Database locked"),
            "Error message should contain original error details"
        );
    }

    #[test]
    fn test_diagnostic_returns_app_version() {
        assert_eq!(APP_VERSION, env!("CARGO_PKG_VERSION"));
    }

    #[test]
    fn test_diagnostic_dto_healthy() {
        let diagnostic = DiagnosticDTO::healthy("0.1.0".to_string());

        assert_eq!(diagnostic.health, "healthy");
        assert!(diagnostic.sqlite_available);
        assert_eq!(diagnostic.app_version, "0.1.0");
        assert_eq!(diagnostic.message, "Application is running normally");
    }

    #[test]
    fn test_diagnostic_dto_sqlite_error() {
        let diagnostic =
            DiagnosticDTO::sqlite_error("0.1.0".to_string(), "Connection failed".to_string());

        assert_eq!(diagnostic.health, "degraded");
        assert!(!diagnostic.sqlite_available);
        assert_eq!(diagnostic.app_version, "0.1.0");
        assert!(diagnostic
            .message
            .contains("SQLite connection check failed"));
        assert!(diagnostic.message.contains("Connection failed"));
    }

    #[test]
    fn test_build_diagnostic_result_when_sqlite_fails() {
        let result = build_diagnostic_result(
            "0.1.0".to_string(),
            false,
            Some("Database connection refused".to_string()),
        );

        assert_eq!(result.health, "degraded");
        assert!(!result.sqlite_available);
        assert_eq!(result.app_version, "0.1.0");
        assert!(result.message.contains("SQLite connection check failed"));
        assert!(result.message.contains("Database connection refused"));
    }

    #[test]
    fn test_build_diagnostic_result_when_sqlite_succeeds() {
        let result = build_diagnostic_result("0.1.0".to_string(), true, None);

        assert_eq!(result.health, "healthy");
        assert!(result.sqlite_available);
        assert_eq!(result.app_version, "0.1.0");
        assert_eq!(result.message, "Application is running normally");
    }
}
