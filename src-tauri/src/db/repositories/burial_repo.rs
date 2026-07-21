use crate::{
    core::models::Burial,
    dto::BurialDTO,
    errors::{AppError, AppResult},
};
use rusqlite::Connection;

pub struct BurialRepository;

impl BurialRepository {
    /// Get a burial by id
    pub fn get(conn: &Connection, id: i64) -> AppResult<BurialDTO> {
        conn.query_row(
            "SELECT id, concession_id, individual_id, buried_at, created_at, updated_at FROM burials WHERE id = ?",
            [id],
            |row| {
                Ok(BurialDTO {
                    id: row.get(0)?,
                    concession_id: row.get(1)?,
                    individual_id: row.get(2)?,
                    buried_at: row.get(3)?,
                    created_at: row.get(4)?,
                    updated_at: row.get(5)?,
                })
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Burial with id {} not found", id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// List burials for a concession, ordered by burial date (newest first, stable id tiebreaker)
    pub fn list_by_concession(conn: &Connection, concession_id: i64) -> AppResult<Vec<BurialDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, concession_id, individual_id, buried_at, created_at, updated_at FROM burials WHERE concession_id = ? ORDER BY buried_at DESC, id DESC"
        )?;

        let burials = stmt.query_map([concession_id], |row| {
            Ok(BurialDTO {
                id: row.get(0)?,
                concession_id: row.get(1)?,
                individual_id: row.get(2)?,
                buried_at: row.get(3)?,
                created_at: row.get(4)?,
                updated_at: row.get(5)?,
            })
        })?;

        burials
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)
    }

    /// Create a new burial
    pub fn create(conn: &Connection, burial: &Burial) -> AppResult<BurialDTO> {
        conn.execute(
            "INSERT INTO burials (concession_id, individual_id, buried_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                burial.concession_id,
                burial.individual_id,
                &burial.buried_at,
                &burial.created_at,
                &burial.updated_at,
            ]
        )?;

        let id = conn.last_insert_rowid();
        Self::get(conn, id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::models::{Cemetery, Concession, Individual};
    use crate::db::migrations::run_migrations;
    use crate::db::repositories::{CemeteryRepository, ConcessionRepository, IndividualRepository};

    fn setup_db() -> Connection {
        let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
        conn.execute("PRAGMA foreign_keys = ON", [])
            .expect("Failed to enable foreign keys");
        run_migrations(&conn).expect("Failed to run migrations");
        conn
    }

    #[test]
    fn test_create_and_get_burial() {
        let conn = setup_db();

        // Create a cemetery
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a concession for the cemetery
        let concession = Concession::new(created_cemetery.id, None);
        let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();

        // Create an individual
        let individual = Individual::new(
            "Deceased Person".to_string(),
            None,
            None,
            "deceased".to_string(),
        );
        let created_individual = IndividualRepository::create(&conn, &individual).unwrap();

        // Create a burial linking the concession and individual
        let burial = Burial::new(created_concession.id, created_individual.id);

        let result = BurialRepository::create(&conn, &burial);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.concession_id, created_concession.id);
        assert_eq!(created.individual_id, created_individual.id);
        assert_eq!(created.buried_at, None);
        assert!(created.id > 0);

        // Verify we can get it back
        let retrieved = BurialRepository::get(&conn, created.id).unwrap();
        assert_eq!(retrieved.id, created.id);
        assert_eq!(retrieved.concession_id, created_concession.id);
        assert_eq!(retrieved.individual_id, created_individual.id);
    }

    #[test]
    fn test_list_by_concession() {
        let conn = setup_db();

        // Create a cemetery
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create two concessions
        let mut concession1 = Concession::new(created_cemetery.id, None);
        concession1.start_date = Some("2026-01-01T00:00:00Z".to_string());

        let mut concession2 = Concession::new(created_cemetery.id, None);
        concession2.start_date = Some("2026-01-01T00:00:00Z".to_string());

        let created_concession1 = ConcessionRepository::create(&conn, &concession1).unwrap();
        let created_concession2 = ConcessionRepository::create(&conn, &concession2).unwrap();

        // Create three individuals
        let individual1 =
            Individual::new("Person 1".to_string(), None, None, "deceased".to_string());
        let individual2 =
            Individual::new("Person 2".to_string(), None, None, "deceased".to_string());
        let individual3 =
            Individual::new("Person 3".to_string(), None, None, "deceased".to_string());
        let created_individual1 = IndividualRepository::create(&conn, &individual1).unwrap();
        let created_individual2 = IndividualRepository::create(&conn, &individual2).unwrap();
        let created_individual3 = IndividualRepository::create(&conn, &individual3).unwrap();

        // Create burials: 2 for concession 1, 1 for concession 2
        let burial1 = Burial::new(created_concession1.id, created_individual1.id);
        let burial2 = Burial::new(created_concession1.id, created_individual2.id);
        let burial3 = Burial::new(created_concession2.id, created_individual3.id);

        BurialRepository::create(&conn, &burial1).unwrap();
        BurialRepository::create(&conn, &burial2).unwrap();
        BurialRepository::create(&conn, &burial3).unwrap();

        // List burials for concession 1
        let burials_1 =
            BurialRepository::list_by_concession(&conn, created_concession1.id).unwrap();
        assert_eq!(burials_1.len(), 2);
        assert!(burials_1
            .iter()
            .all(|b| b.concession_id == created_concession1.id));

        // List burials for concession 2
        let burials_2 =
            BurialRepository::list_by_concession(&conn, created_concession2.id).unwrap();
        assert_eq!(burials_2.len(), 1);
        assert_eq!(burials_2[0].concession_id, created_concession2.id);
    }

    #[test]
    fn test_get_non_existent_burial() {
        let conn = setup_db();

        // Try to get a burial that never existed
        let result = BurialRepository::get(&conn, 999);
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
    fn test_fk_constraint_concession() {
        let conn = setup_db();

        // Create an individual
        let individual = Individual::new("Person".to_string(), None, None, "deceased".to_string());
        let created_individual = IndividualRepository::create(&conn, &individual).unwrap();

        // Try to create a burial with non-existent concession_id
        let burial = Burial::new(9999, created_individual.id);
        let result = BurialRepository::create(&conn, &burial);

        // Should fail with Database error (FK constraint violation)
        assert!(result.is_err());
        match result {
            Err(AppError::Database(_)) => (),
            _ => panic!("Should return Database error for FK constraint violation"),
        }
    }

    #[test]
    fn test_fk_constraint_individual() {
        let conn = setup_db();

        // Create a cemetery and concession
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        let concession = Concession::new(created_cemetery.id, None);
        let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();

        // Try to create a burial with non-existent individual_id
        let burial = Burial::new(created_concession.id, 9999);
        let result = BurialRepository::create(&conn, &burial);

        // Should fail with Database error (FK constraint violation)
        assert!(result.is_err());
        match result {
            Err(AppError::Database(_)) => (),
            _ => panic!("Should return Database error for FK constraint violation"),
        }
    }
}
