use crate::{
    core::models::Concession,
    dto::ConcessionDTO,
    errors::{AppError, AppResult},
};
use chrono::Utc;
use rusqlite::Connection;

pub struct ConcessionRepository;

impl ConcessionRepository {
    pub fn list(conn: &Connection, cemetery_id: Option<i64>) -> AppResult<Vec<ConcessionDTO>> {
        let sql = "SELECT id, cemetery_id, plot_id, concession_number, concession_type, duration_years, start_date, holder_first_name, holder_last_name, holder_address, holder_postal_code, holder_commune, observations, acquired_at, expires_at, renewed_at, status, created_at, updated_at FROM concessions";

        let now = Utc::now();
        match cemetery_id {
            Some(id) => {
                let mut stmt = conn.prepare(&format!(
                    "{} WHERE cemetery_id = ? ORDER BY created_at DESC, id DESC",
                    sql
                ))?;
                let concessions = stmt.query_map([id], |row| Self::map_row_to_dto(row))?;
                concessions
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(AppError::from)?
                    .into_iter()
                    .map(|dto| dto.with_calculated_status(now))
                    .collect()
            }
            None => {
                let mut stmt =
                    conn.prepare(&format!("{} ORDER BY created_at DESC, id DESC", sql))?;
                let concessions = stmt.query_map([], |row| Self::map_row_to_dto(row))?;
                concessions
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(AppError::from)?
                    .into_iter()
                    .map(|dto| dto.with_calculated_status(now))
                    .collect()
            }
        }
    }

    pub fn get(conn: &Connection, id: i64) -> AppResult<ConcessionDTO> {
        let now = Utc::now();
        conn.query_row(
            "SELECT id, cemetery_id, plot_id, concession_number, concession_type, duration_years, start_date, holder_first_name, holder_last_name, holder_address, holder_postal_code, holder_commune, observations, acquired_at, expires_at, renewed_at, status, created_at, updated_at FROM concessions WHERE id = ?",
            [id],
            |row| {
                Self::map_row_to_dto(row)
            }
        )
        .map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Concession with id {} not found", id))
                }
                _ => AppError::Database(err),
            }
        })
        .and_then(|dto| dto.with_calculated_status(now))
    }

    pub fn create(conn: &Connection, concession: &Concession) -> AppResult<ConcessionDTO> {
        let mut concession = concession.clone();
        concession.prepare_for_storage()?;

        if let Some(plot_id) = concession.plot_id {
            if Self::is_plot_occupied_by_active_concession(conn, plot_id)? {
                return Err(AppError::InvalidInput(format!(
                    "Plot {} is already occupied by an active concession",
                    plot_id
                )));
            }
        }

        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, concession_number, concession_type, duration_years, start_date, holder_first_name, holder_last_name, holder_address, holder_postal_code, holder_commune, observations, acquired_at, expires_at, renewed_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                concession.cemetery_id,
                concession.plot_id,
                &concession.concession_number,
                &concession.concession_type,
                &concession.duration_years,
                &concession.start_date,
                &concession.holder_first_name,
                &concession.holder_last_name,
                &concession.holder_address,
                &concession.holder_postal_code,
                &concession.holder_commune,
                &concession.observations,
                &concession.acquired_at,
                &concession.expires_at,
                &concession.renewed_at,
                &concession.status,
                &concession.created_at,
                &concession.updated_at,
            ]
        )?;

        let id = conn.last_insert_rowid();
        Self::get(conn, id)
    }

    pub fn update(conn: &Connection, id: i64, concession: &Concession) -> AppResult<ConcessionDTO> {
        let existing = Self::get(conn, id)?;
        let mut concession = concession.clone();
        concession.prepare_for_storage()?;

        if let Some(plot_id) = concession.plot_id {
            if Some(plot_id) != existing.plot_id
                && Self::is_plot_occupied_by_active_concession(conn, plot_id)?
            {
                return Err(AppError::InvalidInput(format!(
                    "Plot {} is already occupied by an active concession",
                    plot_id
                )));
            }
        }

        conn.execute(
            "UPDATE concessions SET cemetery_id = ?, plot_id = ?, concession_number = ?, concession_type = ?, duration_years = ?, start_date = ?, holder_first_name = ?, holder_last_name = ?, holder_address = ?, holder_postal_code = ?, holder_commune = ?, observations = ?, acquired_at = ?, expires_at = ?, renewed_at = ?, status = ?, updated_at = ? WHERE id = ?",
            rusqlite::params![
                concession.cemetery_id,
                concession.plot_id,
                &concession.concession_number,
                &concession.concession_type,
                &concession.duration_years,
                &concession.start_date,
                &concession.holder_first_name,
                &concession.holder_last_name,
                &concession.holder_address,
                &concession.holder_postal_code,
                &concession.holder_commune,
                &concession.observations,
                &concession.acquired_at,
                &concession.expires_at,
                &concession.renewed_at,
                &concession.status,
                &concession.updated_at,
                id,
            ]
        )?;

        Self::get(conn, id)
    }

    fn is_plot_occupied_by_active_concession(conn: &Connection, plot_id: i64) -> AppResult<bool> {
        let now = Utc::now().to_rfc3339();
        let mut stmt = conn.prepare(
            "SELECT COUNT(*) FROM concessions WHERE plot_id = ? AND (UPPER(status) = 'PERPETUELLE' OR (UPPER(status) IN ('ACTIVE', 'ECHEANCE_PROCHE') AND (expires_at IS NULL OR expires_at > ?)))"
        )?;
        let count: i64 = stmt.query_row(rusqlite::params![plot_id, &now], |row| row.get(0))?;
        Ok(count > 0)
    }

    fn map_row_to_dto(row: &rusqlite::Row) -> rusqlite::Result<ConcessionDTO> {
        Ok(ConcessionDTO {
            id: row.get(0)?,
            cemetery_id: row.get(1)?,
            plot_id: row.get(2)?,
            concession_number: row.get(3)?,
            concession_type: row.get(4)?,
            duration_years: row.get(5)?,
            start_date: row.get(6)?,
            holder_first_name: row.get(7)?,
            holder_last_name: row.get(8)?,
            holder_address: row.get(9)?,
            holder_postal_code: row.get(10)?,
            holder_commune: row.get(11)?,
            observations: row.get(12)?,
            acquired_at: row.get(13)?,
            expires_at: row.get(14)?,
            renewed_at: row.get(15)?,
            status: row.get(16)?,
            created_at: row.get(17)?,
            updated_at: row.get(18)?,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::models::{Cemetery, Plot};
    use crate::db::migrations::run_migrations;
    use crate::db::repositories::{CemeteryRepository, PlotRepository};
    use chrono::Utc;

    fn setup_db() -> Connection {
        let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
        conn.execute("PRAGMA foreign_keys = ON", [])
            .expect("Failed to enable foreign keys");
        run_migrations(&conn).expect("Failed to run migrations");
        conn
    }

    #[test]
    fn test_create_and_get_concession() {
        let conn = setup_db();

        // Create a test cemetery first (foreign key requirement)
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a concession for the cemetery (default is PERPETUELLE)
        let concession = Concession::new(created_cemetery.id, None);

        let result = ConcessionRepository::create(&conn, &concession);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.cemetery_id, created_cemetery.id);
        assert_eq!(created.plot_id, None);
        assert_eq!(created.concession_type, "PERPETUELLE");
        assert_eq!(created.status, "PERPETUELLE");
        assert!(created.id > 0);

        // Verify we can get it back
        let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();
        assert_eq!(retrieved.id, created.id);
        assert_eq!(retrieved.cemetery_id, created_cemetery.id);
        assert_eq!(retrieved.status, "PERPETUELLE");
    }

    #[test]
    fn test_list_concessions() {
        let conn = setup_db();

        // Create a test cemetery
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create another cemetery for filtering test
        let cemetery2 = Cemetery::new(
            "Other Cemetery".to_string(),
            Some("Other City".to_string()),
            Some(300),
        );
        let created_cemetery2 = CemeteryRepository::create(&conn, &cemetery2).unwrap();

        // Create concessions for both cemeteries
        let concession1 = Concession::new(created_cemetery.id, None);
        let concession2 = Concession::new(created_cemetery.id, None);
        let concession3 = Concession::new(created_cemetery2.id, None);

        ConcessionRepository::create(&conn, &concession1).unwrap();
        ConcessionRepository::create(&conn, &concession2).unwrap();
        ConcessionRepository::create(&conn, &concession3).unwrap();

        // List all concessions for the first cemetery
        let concessions = ConcessionRepository::list(&conn, Some(created_cemetery.id)).unwrap();
        assert_eq!(concessions.len(), 2);
        assert!(concessions
            .iter()
            .all(|c| c.cemetery_id == created_cemetery.id));

        // List all concessions (no filter)
        let all_concessions = ConcessionRepository::list(&conn, None).unwrap();
        assert_eq!(all_concessions.len(), 3);
    }

    #[test]
    fn test_update_concession() {
        let conn = setup_db();

        // Create a test cemetery
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a concession (default is PERPETUELLE)
        let concession = Concession::new(created_cemetery.id, None);
        let created = ConcessionRepository::create(&conn, &concession).unwrap();
        let id = created.id;
        assert_eq!(created.status, "PERPETUELLE");

        // Update the concession with holder data
        let mut updated_concession = concession;
        updated_concession.id = id;
        updated_concession.holder_first_name = Some("John".to_string());
        updated_concession.updated_at = Utc::now().to_rfc3339();

        let updated = ConcessionRepository::update(&conn, id, &updated_concession).unwrap();
        assert_eq!(updated.id, id);
        assert_eq!(updated.holder_first_name, Some("John".to_string()));
        assert_eq!(updated.status, "PERPETUELLE");

        // Verify the update persisted
        let retrieved = ConcessionRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.holder_first_name, Some("John".to_string()));
        assert_eq!(retrieved.status, "PERPETUELLE");
    }

    #[test]
    fn test_get_non_existent_concession() {
        let conn = setup_db();

        // Try to get a concession that never existed
        let result = ConcessionRepository::get(&conn, 999);
        assert!(result.is_err());

        // Verify it's a NotFound error, not a Database error
        match result {
            Err(AppError::NotFound(msg)) => {
                assert!(msg.contains("999"));
            }
            Err(AppError::Database(_)) => {
                panic!("Should return NotFound, not Database error");
            }
            Err(AppError::InvalidInput(_)) | Err(AppError::Internal(_)) => {
                panic!("Should return NotFound, not other error variant");
            }
            Ok(_) => panic!("Should return an error"),
        }
    }

    #[test]
    fn test_update_non_existent_concession() {
        let conn = setup_db();

        // Create a test cemetery for valid FK
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a concession template
        let concession = Concession::new(created_cemetery.id, None);

        // Try to update a concession that never existed
        let result = ConcessionRepository::update(&conn, 999, &concession);
        assert!(result.is_err());

        // Verify it's a NotFound error
        match result {
            Err(AppError::NotFound(_)) => (),
            _ => panic!("Should return NotFound error"),
        }
    }

    #[test]
    fn test_fk_constraint_cemetery() {
        let conn = setup_db();

        // Try to create a concession with non-existent cemetery_id
        let concession = Concession::new(9999, None);
        let result = ConcessionRepository::create(&conn, &concession);

        // Should fail with Database error (FK constraint violation)
        assert!(result.is_err());
        match result {
            Err(AppError::Database(_)) => (),
            _ => panic!("Should return Database error for FK constraint violation"),
        }
    }

    #[test]
    fn test_temporaire_validation_requires_start_date() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.duration_years = Some(15);
        concession.start_date = None;

        let result = concession.validate();
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("start_date"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[test]
    fn test_temporaire_validation_requires_duration() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.duration_years = None;
        concession.start_date = Some("2025-01-01T00:00:00Z".to_string());

        let result = concession.validate();
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("duration_years"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[test]
    fn test_temporaire_validation_duration_range() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.start_date = Some("2025-01-01T00:00:00Z".to_string());

        // Test duration too low
        concession.duration_years = Some(0);
        assert!(concession.validate().is_err());

        // Test duration too high
        concession.duration_years = Some(100);
        assert!(concession.validate().is_err());

        // Test valid range
        concession.duration_years = Some(1);
        assert!(concession.validate().is_ok());

        concession.duration_years = Some(50);
        assert!(concession.validate().is_ok());

        concession.duration_years = Some(99);
        assert!(concession.validate().is_ok());
    }

    #[test]
    fn test_trentenaire_validation_requires_start_date() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TRENTENAIRE".to_string();
        concession.duration_years = Some(30);
        concession.start_date = None;

        let result = concession.validate();
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("start_date"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[test]
    fn test_trentenaire_validation_requires_30_years() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TRENTENAIRE".to_string();
        concession.duration_years = Some(20);
        concession.start_date = Some("2025-01-01T00:00:00Z".to_string());

        let result = concession.validate();
        assert!(result.is_err());

        concession.duration_years = Some(30);
        assert!(concession.validate().is_ok());
    }

    #[test]
    fn test_cinquantenaire_validation_requires_start_date() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "CINQUANTENAIRE".to_string();
        concession.duration_years = Some(50);
        concession.start_date = None;

        let result = concession.validate();
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("start_date"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[test]
    fn test_cinquantenaire_validation_requires_50_years() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "CINQUANTENAIRE".to_string();
        concession.duration_years = Some(40);
        concession.start_date = Some("2025-01-01T00:00:00Z".to_string());

        let result = concession.validate();
        assert!(result.is_err());

        concession.duration_years = Some(50);
        assert!(concession.validate().is_ok());
    }

    #[test]
    fn test_perpetuelle_validation_no_duration() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "PERPETUELLE".to_string();
        concession.duration_years = Some(100);

        let result = concession.validate();
        assert!(result.is_err());

        concession.duration_years = None;
        assert!(concession.validate().is_ok());
    }

    #[test]
    fn test_expires_at_calculation_perpetuelle() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "PERPETUELLE".to_string();

        let expires_at = concession.calculate_expires_at().unwrap();
        assert_eq!(expires_at, None);
    }

    #[test]
    fn test_expires_at_calculation_temporaire() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.duration_years = Some(15);
        concession.start_date = Some("2025-01-01T00:00:00Z".to_string());

        let expires_at = concession.calculate_expires_at().unwrap();
        assert!(expires_at.is_some());

        let expires = expires_at.unwrap();
        assert!(expires.contains("2040"));
    }

    #[test]
    fn test_expires_at_calculation_leap_year_feb29() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.duration_years = Some(4);
        concession.start_date = Some("2020-02-29T00:00:00Z".to_string());

        let expires_at = concession.calculate_expires_at().unwrap();
        assert!(expires_at.is_some());

        let expires = expires_at.unwrap();
        assert!(expires.starts_with("2024-02-29"));
    }

    #[test]
    fn test_expires_at_calculation_leap_year_edge_case() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.duration_years = Some(1);
        concession.start_date = Some("2024-02-29T00:00:00Z".to_string());

        let expires_at = concession.calculate_expires_at().unwrap();
        assert!(expires_at.is_some());

        let expires = expires_at.unwrap();
        assert!(expires.contains("2025-02-28T") || expires.contains("2025-03-01T"));
    }

    #[test]
    fn test_status_calculation_perpetuelle() {
        let conn = setup_db();
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        let concession = Concession::new(created_cemetery.id, None);
        let created = ConcessionRepository::create(&conn, &concession).unwrap();

        assert_eq!(created.concession_type, "PERPETUELLE");
        assert_eq!(created.status, "PERPETUELLE");

        // Verify that subsequent reads also return PERPETUELLE status (not the stored value)
        let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();
        assert_eq!(retrieved.concession_type, "PERPETUELLE");
        assert_eq!(retrieved.status, "PERPETUELLE");

        // Verify in list view as well
        let list = ConcessionRepository::list(&conn, Some(created_cemetery.id)).unwrap();
        let found = list.iter().find(|c| c.id == created.id).unwrap();
        assert_eq!(found.status, "PERPETUELLE");
    }

    #[test]
    fn test_status_calculation_with_reference_date() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.duration_years = Some(10);
        concession.start_date = Some("2023-01-01T00:00:00Z".to_string());

        concession.prepare_for_storage().unwrap();

        let reference_date = chrono::DateTime::parse_from_rfc3339("2032-12-31T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let status = concession.calculate_status(reference_date).unwrap();

        assert_eq!(status, crate::core::models::ConcessionStatus::SoonExpiring);
    }

    #[test]
    fn test_status_echeance_proche_12_months_boundary() {
        let mut concession = Concession::new(1, None);
        concession.concession_type = "TEMPORAIRE".to_string();
        concession.duration_years = Some(10);
        concession.start_date = Some("2024-01-01T00:00:00Z".to_string());
        concession.prepare_for_storage().unwrap();

        // Expire at 2034-01-01

        // 367 days before expiry -> ACTIVE (outside 12-month window)
        let reference_date_367_days = chrono::DateTime::parse_from_rfc3339("2032-12-30T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let status_367 = concession
            .calculate_status(reference_date_367_days)
            .unwrap();
        assert_eq!(status_367, crate::core::models::ConcessionStatus::Active);

        // 366 days before expiry -> ECHEANCE_PROCHE (within 12-month window)
        let reference_date_366_days = chrono::DateTime::parse_from_rfc3339("2032-12-31T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let status_366 = concession
            .calculate_status(reference_date_366_days)
            .unwrap();
        assert_eq!(
            status_366,
            crate::core::models::ConcessionStatus::SoonExpiring
        );

        // 1 day before expiry -> ECHEANCE_PROCHE
        let reference_date_1_day = chrono::DateTime::parse_from_rfc3339("2033-12-31T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let status_1 = concession.calculate_status(reference_date_1_day).unwrap();
        assert_eq!(
            status_1,
            crate::core::models::ConcessionStatus::SoonExpiring
        );
    }

    #[test]
    fn test_concession_with_holder_data() {
        let conn = setup_db();
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        let mut concession = Concession::new(created_cemetery.id, None);
        concession.holder_first_name = Some("Jean".to_string());
        concession.holder_last_name = Some("Dupont".to_string());
        concession.holder_address = Some("123 Rue de la Paix".to_string());
        concession.holder_postal_code = Some("75000".to_string());
        concession.holder_commune = Some("Paris".to_string());

        let created = ConcessionRepository::create(&conn, &concession).unwrap();

        assert_eq!(created.holder_first_name, Some("Jean".to_string()));
        assert_eq!(created.holder_last_name, Some("Dupont".to_string()));
        assert_eq!(
            created.holder_address,
            Some("123 Rue de la Paix".to_string())
        );
    }

    #[test]
    fn test_plot_occupation_validation() {
        let conn = setup_db();
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        let plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(1),
            10,
        );
        let created_plot = PlotRepository::create(&conn, &plot).unwrap();

        // Create first concession on the plot (PERPETUELLE)
        let concession1 = Concession::new(created_cemetery.id, Some(created_plot.id));
        let created1 = ConcessionRepository::create(&conn, &concession1).unwrap();
        assert_eq!(created1.plot_id, Some(created_plot.id));

        // Try to create second concession on the same plot - should fail (plot occupied by PERPETUELLE)
        let concession2 = Concession::new(created_cemetery.id, Some(created_plot.id));
        let result = ConcessionRepository::create(&conn, &concession2);
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("already occupied"));
            }
            _ => panic!("Expected InvalidInput error for occupied plot"),
        }
    }

    #[test]
    fn test_plot_occupation_expired_concession_allows_new() {
        let conn = setup_db();
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        let plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(1),
            10,
        );
        let created_plot = PlotRepository::create(&conn, &plot).unwrap();

        // Create a temporary concession that expires in the past
        let mut concession1 = Concession::new(created_cemetery.id, Some(created_plot.id));
        concession1.concession_type = "TEMPORAIRE".to_string();
        concession1.duration_years = Some(1);
        concession1.start_date = Some("2020-01-01T00:00:00Z".to_string());
        concession1.status = "expired".to_string();
        let created1 = ConcessionRepository::create(&conn, &concession1).unwrap();
        assert_eq!(created1.status, "EXPIREE");

        // Create second concession on the same plot - should succeed (expired plot is free)
        let concession2 = Concession::new(created_cemetery.id, Some(created_plot.id));
        let result = ConcessionRepository::create(&conn, &concession2);
        assert!(result.is_ok());
        let created2 = result.unwrap();
        assert_eq!(created2.plot_id, Some(created_plot.id));
    }
}
