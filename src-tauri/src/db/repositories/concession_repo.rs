use crate::{
    core::models::Concession,
    dto::ConcessionDTO,
    errors::{AppError, AppResult},
};
use rusqlite::Connection;

pub struct ConcessionRepository;

impl ConcessionRepository {
    /// List concessions, optionally filtered by cemetery_id, ordered by creation date (newest first, stable id tiebreaker)
    pub fn list(conn: &Connection, cemetery_id: Option<i64>) -> AppResult<Vec<ConcessionDTO>> {
        match cemetery_id {
            Some(id) => {
                let mut stmt = conn.prepare(
                    "SELECT id, cemetery_id, plot_id, acquired_at, expires_at, renewed_at, status, created_at, updated_at FROM concessions WHERE cemetery_id = ? ORDER BY created_at DESC, id DESC"
                )?;
                let concessions = stmt.query_map([id], |row| {
                    Ok(ConcessionDTO {
                        id: row.get(0)?,
                        cemetery_id: row.get(1)?,
                        plot_id: row.get(2)?,
                        acquired_at: row.get(3)?,
                        expires_at: row.get(4)?,
                        renewed_at: row.get(5)?,
                        status: row.get(6)?,
                        created_at: row.get(7)?,
                        updated_at: row.get(8)?,
                    })
                })?;
                concessions
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(AppError::from)
            }
            None => {
                let mut stmt = conn.prepare(
                    "SELECT id, cemetery_id, plot_id, acquired_at, expires_at, renewed_at, status, created_at, updated_at FROM concessions ORDER BY created_at DESC, id DESC"
                )?;
                let concessions = stmt.query_map([], |row| {
                    Ok(ConcessionDTO {
                        id: row.get(0)?,
                        cemetery_id: row.get(1)?,
                        plot_id: row.get(2)?,
                        acquired_at: row.get(3)?,
                        expires_at: row.get(4)?,
                        renewed_at: row.get(5)?,
                        status: row.get(6)?,
                        created_at: row.get(7)?,
                        updated_at: row.get(8)?,
                    })
                })?;
                concessions
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(AppError::from)
            }
        }
    }

    /// Get a concession by id
    pub fn get(conn: &Connection, id: i64) -> AppResult<ConcessionDTO> {
        conn.query_row(
            "SELECT id, cemetery_id, plot_id, acquired_at, expires_at, renewed_at, status, created_at, updated_at FROM concessions WHERE id = ?",
            [id],
            |row| {
                Ok(ConcessionDTO {
                    id: row.get(0)?,
                    cemetery_id: row.get(1)?,
                    plot_id: row.get(2)?,
                    acquired_at: row.get(3)?,
                    expires_at: row.get(4)?,
                    renewed_at: row.get(5)?,
                    status: row.get(6)?,
                    created_at: row.get(7)?,
                    updated_at: row.get(8)?,
                })
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Concession with id {} not found", id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Create a new concession
    pub fn create(conn: &Connection, concession: &Concession) -> AppResult<ConcessionDTO> {
        conn.execute(
            "INSERT INTO concessions (cemetery_id, plot_id, acquired_at, expires_at, renewed_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                concession.cemetery_id,
                concession.plot_id,
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

    /// Update a concession
    pub fn update(conn: &Connection, id: i64, concession: &Concession) -> AppResult<ConcessionDTO> {
        // First check if the concession exists
        let _existing = Self::get(conn, id)?;

        conn.execute(
            "UPDATE concessions SET cemetery_id = ?, plot_id = ?, acquired_at = ?, expires_at = ?, renewed_at = ?, status = ?, updated_at = ? WHERE id = ?",
            rusqlite::params![
                concession.cemetery_id,
                concession.plot_id,
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
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::models::Cemetery;
    use crate::db::migrations::run_migrations;
    use crate::db::repositories::CemeteryRepository;

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

        // Create a concession for the cemetery
        let concession = Concession::new(created_cemetery.id, None);

        let result = ConcessionRepository::create(&conn, &concession);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.cemetery_id, created_cemetery.id);
        assert_eq!(created.plot_id, None);
        assert_eq!(created.status, "active");
        assert!(created.id > 0);

        // Verify we can get it back
        let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();
        assert_eq!(retrieved.id, created.id);
        assert_eq!(retrieved.cemetery_id, created_cemetery.id);
        assert_eq!(retrieved.status, "active");
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

        // Create a concession
        let concession = Concession::new(created_cemetery.id, None);
        let created = ConcessionRepository::create(&conn, &concession).unwrap();
        let id = created.id;

        // Update the concession status
        let mut updated_concession = concession;
        updated_concession.id = id;
        updated_concession.status = "expired".to_string();
        updated_concession.updated_at = chrono::Utc::now().to_rfc3339();

        let updated = ConcessionRepository::update(&conn, id, &updated_concession).unwrap();
        assert_eq!(updated.id, id);
        assert_eq!(updated.status, "expired");

        // Verify the update persisted
        let retrieved = ConcessionRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.status, "expired");
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
}
