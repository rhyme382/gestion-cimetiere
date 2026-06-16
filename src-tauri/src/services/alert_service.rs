use crate::db::repositories::AlertRepository;
use crate::dto::{AlertDTO, AlertType};
use crate::errors::{AppError, AppResult};
use rusqlite::Connection;

pub struct AlertService;

impl AlertService {
    /// Calculate and store alerts for all concessions based on expiry dates
    pub fn calculate_alerts(conn: &Connection) -> AppResult<Vec<AlertDTO>> {
        // Get all active concessions with expiry dates
        let mut stmt = conn.prepare(
            "SELECT id, expires_at FROM concessions WHERE status IN ('active', 'renewed') AND expires_at IS NOT NULL"
        ).map_err(AppError::from)?;

        let concessions: Vec<(i64, String)> = stmt
            .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))?
            .collect::<rusqlite::Result<Vec<_>>>()
            .map_err(AppError::from)?;

        let mut created_alerts = Vec::new();

        for (concession_id, expires_at) in concessions {
            // Calculate days until expiry
            let days_until: i32 = conn
                .query_row(
                    "SELECT CAST((julianday(?) - julianday('now')) AS INTEGER)",
                    rusqlite::params![&expires_at],
                    |row| row.get(0),
                )
                .unwrap_or(-1);

            if days_until < 0 {
                continue; // Already expired, skip
            }

            // Determine alert type based on threshold
            let alert_type = if days_until <= 30 {
                AlertType::Critical
            } else if days_until <= 90 {
                AlertType::Warning
            } else if days_until <= 180 {
                AlertType::Info
            } else {
                continue; // No alert needed
            };

            // Check if alert already exists and is not acknowledged
            let existing = conn.query_row(
                "SELECT COUNT(*) FROM alerts WHERE concession_id = ? AND acknowledged_at IS NULL",
                rusqlite::params![concession_id],
                |row| row.get::<_, i64>(0),
            ).unwrap_or(0);

            if existing == 0 {
                // Create new alert
                let alert = AlertRepository::create(
                    conn,
                    concession_id,
                    alert_type,
                    &expires_at,
                    days_until,
                )?;
                created_alerts.push(alert);
            }
        }

        Ok(created_alerts)
    }

    /// Get thresholds for alert types (in days)
    pub fn get_thresholds() -> AlertThresholds {
        AlertThresholds {
            critical: 30,
            warning: 90,
            info: 180,
        }
    }
}

pub struct AlertThresholds {
    pub critical: i32,
    pub warning: i32,
    pub info: i32,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> Connection {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        conn.execute_batch("PRAGMA foreign_keys = OFF;").unwrap();

        let migrations = vec![
            include_str!("../../migrations/001_initial_schema.sql"),
            include_str!("../../migrations/0006_create_alerts_table.sql"),
        ];
        for migration in migrations {
            conn.execute_batch(migration).unwrap();
        }
        conn
    }

    #[test]
    fn test_get_thresholds() {
        let thresholds = AlertService::get_thresholds();
        assert_eq!(thresholds.critical, 30);
        assert_eq!(thresholds.warning, 90);
        assert_eq!(thresholds.info, 180);
    }

    #[test]
    fn test_calculate_alerts_no_concessions() {
        let conn = setup();
        let alerts = AlertService::calculate_alerts(&conn).unwrap();
        assert!(alerts.is_empty());
    }

    #[test]
    fn test_calculate_alerts_no_expiry_dates() {
        let conn = setup();
        conn.execute(
            "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
            rusqlite::params![
                "Test Cemetery",
                "2026-06-16 10:00:00",
                "2026-06-16 10:00:00"
            ],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![1, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();

        let alerts = AlertService::calculate_alerts(&conn).unwrap();
        assert!(alerts.is_empty());
    }
}
