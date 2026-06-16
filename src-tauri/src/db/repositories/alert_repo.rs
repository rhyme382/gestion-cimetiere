use crate::dto::{AlertDTO, AlertSummaryDTO, AlertType};
use crate::errors::{AppError, AppResult};
use rusqlite::Connection;

pub struct AlertRepository;

impl AlertRepository {
    /// Create a new alert for a concession
    pub fn create(
        conn: &Connection,
        concession_id: i64,
        alert_type: AlertType,
        expected_expiry_date: &str,
        days_until_expiry: i32,
    ) -> AppResult<AlertDTO> {
        conn.execute(
            "INSERT INTO alerts (concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at)
             VALUES (?, ?, ?, ?, datetime('now'))",
            rusqlite::params![concession_id, alert_type.as_str(), expected_expiry_date, days_until_expiry],
        ).map_err(AppError::from)?;

        let id = conn.last_insert_rowid();
        Self::get(conn, id)
    }

    /// Retrieve all alerts
    pub fn list(conn: &Connection) -> AppResult<Vec<AlertDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at, acknowledged_at
             FROM alerts
             ORDER BY created_at DESC, id DESC",
        ).map_err(AppError::from)?;

        let alerts = stmt
            .query_map([], |row| {
                Ok(AlertDTO {
                    id: row.get(0)?,
                    concession_id: row.get(1)?,
                    alert_type: AlertType::from_str(&row.get::<_, String>(2)?).unwrap(),
                    expected_expiry_date: row.get(3)?,
                    days_until_expiry: row.get(4)?,
                    created_at: row.get(5)?,
                    acknowledged_at: row.get(6)?,
                })
            })
            .map_err(AppError::from)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)?;

        Ok(alerts)
    }

    /// Retrieve unacknowledged alerts
    pub fn list_unacknowledged(conn: &Connection) -> AppResult<Vec<AlertDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at, acknowledged_at
             FROM alerts
             WHERE acknowledged_at IS NULL
             ORDER BY created_at DESC, id DESC",
        ).map_err(AppError::from)?;

        let alerts = stmt
            .query_map([], |row| {
                Ok(AlertDTO {
                    id: row.get(0)?,
                    concession_id: row.get(1)?,
                    alert_type: AlertType::from_str(&row.get::<_, String>(2)?).unwrap(),
                    expected_expiry_date: row.get(3)?,
                    days_until_expiry: row.get(4)?,
                    created_at: row.get(5)?,
                    acknowledged_at: row.get(6)?,
                })
            })
            .map_err(AppError::from)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)?;

        Ok(alerts)
    }

    /// Retrieve a single alert by ID
    pub fn get(conn: &Connection, id: i64) -> AppResult<AlertDTO> {
        conn.query_row(
            "SELECT id, concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at, acknowledged_at
             FROM alerts WHERE id = ?",
            rusqlite::params![id],
            |row| {
                Ok(AlertDTO {
                    id: row.get(0)?,
                    concession_id: row.get(1)?,
                    alert_type: AlertType::from_str(&row.get::<_, String>(2)?).unwrap(),
                    expected_expiry_date: row.get(3)?,
                    days_until_expiry: row.get(4)?,
                    created_at: row.get(5)?,
                    acknowledged_at: row.get(6)?,
                })
            },
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Alert with id {} not found", id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Retrieve alerts for a specific concession
    pub fn get_by_concession(conn: &Connection, concession_id: i64) -> AppResult<Vec<AlertDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, concession_id, alert_type, expected_expiry_date, days_until_expiry, created_at, acknowledged_at
             FROM alerts
             WHERE concession_id = ?
             ORDER BY created_at DESC, id DESC",
        ).map_err(AppError::from)?;

        let alerts = stmt
            .query_map(rusqlite::params![concession_id], |row| {
                Ok(AlertDTO {
                    id: row.get(0)?,
                    concession_id: row.get(1)?,
                    alert_type: AlertType::from_str(&row.get::<_, String>(2)?).unwrap(),
                    expected_expiry_date: row.get(3)?,
                    days_until_expiry: row.get(4)?,
                    created_at: row.get(5)?,
                    acknowledged_at: row.get(6)?,
                })
            })
            .map_err(AppError::from)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)?;

        Ok(alerts)
    }

    /// Mark an alert as acknowledged
    pub fn acknowledge(conn: &Connection, id: i64) -> AppResult<bool> {
        let rows_affected = conn.execute(
            "UPDATE alerts SET acknowledged_at = datetime('now') WHERE id = ? AND acknowledged_at IS NULL",
            rusqlite::params![id],
        ).map_err(AppError::from)?;

        Ok(rows_affected > 0)
    }

    /// Get aggregated alert summary
    pub fn get_summary(conn: &Connection) -> AppResult<AlertSummaryDTO> {
        let total_alerts: i32 = conn
            .query_row(
                "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL",
                [],
                |row| row.get(0),
            )
            .map_err(AppError::from)?;

        let critical_count: i32 = conn.query_row(
            "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL AND alert_type = 'CRITICAL'",
            [],
            |row| row.get(0),
        ).map_err(AppError::from)?;

        let warning_count: i32 = conn.query_row(
            "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL AND alert_type = 'WARNING'",
            [],
            |row| row.get(0),
        ).map_err(AppError::from)?;

        let info_count: i32 = conn
            .query_row(
                "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL AND alert_type = 'INFO'",
                [],
                |row| row.get(0),
            )
            .map_err(AppError::from)?;

        Ok(AlertSummaryDTO {
            total_alerts,
            critical_count,
            warning_count,
            info_count,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> Connection {
        let conn = rusqlite::Connection::open_in_memory().unwrap();

        // Disable foreign keys for testing
        conn.execute_batch("PRAGMA foreign_keys = OFF;").unwrap();

        let initial_migration = include_str!("../../../migrations/001_initial_schema.sql");
        let alert_migration = include_str!("../../../migrations/0006_create_alerts_table.sql");

        conn.execute_batch(initial_migration).unwrap();
        conn.execute_batch(alert_migration).unwrap();

        conn
    }

    #[test]
    fn test_create_alert() {
        let conn = setup();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();

        let result = AlertRepository::create(&conn, 1, AlertType::Critical, "2026-07-15", 29);

        assert!(result.is_ok());
        let alert = result.unwrap();
        assert_eq!(alert.concession_id, 1);
        assert_eq!(alert.alert_type, AlertType::Critical);
    }

    #[test]
    fn test_list_alerts() {
        let conn = setup();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();

        AlertRepository::create(&conn, 1, AlertType::Warning, "2026-08-15", 60).unwrap();
        AlertRepository::create(&conn, 1, AlertType::Info, "2026-12-15", 183).unwrap();

        let alerts = AlertRepository::list(&conn).unwrap();
        assert_eq!(alerts.len(), 2);
    }

    #[test]
    fn test_list_unacknowledged_alerts() {
        let conn = setup();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();

        let alert =
            AlertRepository::create(&conn, 1, AlertType::Critical, "2026-07-15", 29).unwrap();
        AlertRepository::acknowledge(&conn, alert.id).unwrap();

        let alerts = AlertRepository::list_unacknowledged(&conn).unwrap();
        assert!(alerts.is_empty());
    }

    #[test]
    fn test_acknowledge_alert() {
        let conn = setup();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();

        let alert =
            AlertRepository::create(&conn, 1, AlertType::Critical, "2026-07-15", 29).unwrap();
        let result = AlertRepository::acknowledge(&conn, alert.id);

        assert!(result.is_ok());
        assert!(result.unwrap());

        let acknowledged = AlertRepository::get(&conn, alert.id).unwrap();
        assert!(acknowledged.acknowledged_at.is_some());
    }

    #[test]
    fn test_get_alert_summary() {
        let conn = setup();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();

        AlertRepository::create(&conn, 1, AlertType::Critical, "2026-07-15", 29).unwrap();
        AlertRepository::create(&conn, 1, AlertType::Critical, "2026-07-20", 34).unwrap();
        AlertRepository::create(&conn, 1, AlertType::Warning, "2026-08-15", 60).unwrap();
        AlertRepository::create(&conn, 1, AlertType::Info, "2026-12-15", 183).unwrap();

        let summary = AlertRepository::get_summary(&conn).unwrap();
        assert_eq!(summary.total_alerts, 4);
        assert_eq!(summary.critical_count, 2);
        assert_eq!(summary.warning_count, 1);
        assert_eq!(summary.info_count, 1);
    }

    #[test]
    fn test_get_alerts_by_concession() {
        let conn = setup();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 1, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, 2, "active", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();

        AlertRepository::create(&conn, 1, AlertType::Critical, "2026-07-15", 29).unwrap();
        AlertRepository::create(&conn, 2, AlertType::Warning, "2026-08-15", 60).unwrap();

        let alerts_1 = AlertRepository::get_by_concession(&conn, 1).unwrap();
        assert_eq!(alerts_1.len(), 1);
        assert_eq!(alerts_1[0].concession_id, 1);

        let alerts_2 = AlertRepository::get_by_concession(&conn, 2).unwrap();
        assert_eq!(alerts_2.len(), 1);
        assert_eq!(alerts_2[0].concession_id, 2);
    }
}
