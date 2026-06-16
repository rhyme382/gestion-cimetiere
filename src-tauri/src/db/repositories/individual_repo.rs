use crate::{
    core::models::Individual,
    dto::IndividualDTO,
    errors::{AppError, AppResult},
};
use rusqlite::Connection;

pub struct IndividualRepository;

impl IndividualRepository {
    /// List all individuals ordered by name
    pub fn list(conn: &Connection) -> AppResult<Vec<IndividualDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, name, email, phone, role, created_at, updated_at FROM individuals ORDER BY name"
        )?;

        let individuals = stmt.query_map([], |row| {
            Ok(IndividualDTO {
                id: row.get(0)?,
                name: row.get(1)?,
                email: row.get(2)?,
                phone: row.get(3)?,
                role: row.get(4)?,
                created_at: row.get(5)?,
                updated_at: row.get(6)?,
            })
        })?;

        individuals
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)
    }

    /// Get an individual by id
    pub fn get(conn: &Connection, id: i64) -> AppResult<IndividualDTO> {
        conn.query_row(
            "SELECT id, name, email, phone, role, created_at, updated_at FROM individuals WHERE id = ?",
            [id],
            |row| {
                Ok(IndividualDTO {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    email: row.get(2)?,
                    phone: row.get(3)?,
                    role: row.get(4)?,
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Individual with id {} not found", id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Create a new individual
    pub fn create(conn: &Connection, individual: &Individual) -> AppResult<IndividualDTO> {
        conn.execute(
            "INSERT INTO individuals (name, email, phone, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                &individual.name,
                &individual.email,
                &individual.phone,
                &individual.role,
                &individual.created_at,
                &individual.updated_at,
            ]
        )?;

        let id = conn.last_insert_rowid();
        Self::get(conn, id)
    }

    /// Update an individual
    pub fn update(conn: &Connection, id: i64, individual: &Individual) -> AppResult<IndividualDTO> {
        // First check if the individual exists
        let _existing = Self::get(conn, id)?;

        conn.execute(
            "UPDATE individuals SET name = ?, email = ?, phone = ?, role = ?, updated_at = ? WHERE id = ?",
            rusqlite::params![
                &individual.name,
                &individual.email,
                &individual.phone,
                &individual.role,
                &individual.updated_at,
                id,
            ]
        )?;

        Self::get(conn, id)
    }

    /// Search individuals by name, email, or phone
    pub fn search(conn: &Connection, query: &str) -> AppResult<Vec<IndividualDTO>> {
        let search_pattern = format!("%{}%", query);
        let mut stmt = conn.prepare(
            "SELECT id, name, email, phone, role, created_at, updated_at FROM individuals WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? ORDER BY name"
        )?;

        let individuals = stmt.query_map(
            rusqlite::params![&search_pattern, &search_pattern, &search_pattern],
            |row| {
                Ok(IndividualDTO {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    email: row.get(2)?,
                    phone: row.get(3)?,
                    role: row.get(4)?,
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            },
        )?;

        individuals
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::migrations::run_migrations;

    fn setup_db() -> Connection {
        let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
        conn.execute("PRAGMA foreign_keys = ON", [])
            .expect("Failed to enable foreign keys");
        run_migrations(&conn).expect("Failed to run migrations");
        conn
    }

    #[test]
    fn test_create_and_get_individual() {
        let conn = setup_db();

        let individual = Individual::new(
            "Jean Dupont".to_string(),
            Some("jean@example.com".to_string()),
            Some("06123456789".to_string()),
            "family".to_string(),
        );

        let result = IndividualRepository::create(&conn, &individual);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.name, "Jean Dupont");
        assert_eq!(created.email, Some("jean@example.com".to_string()));
        assert_eq!(created.phone, Some("06123456789".to_string()));
        assert_eq!(created.role, "family");
        assert!(created.id > 0);

        // Verify we can get it back
        let retrieved = IndividualRepository::get(&conn, created.id).unwrap();
        assert_eq!(retrieved.id, created.id);
        assert_eq!(retrieved.name, "Jean Dupont");
        assert_eq!(retrieved.email, Some("jean@example.com".to_string()));
        assert_eq!(retrieved.phone, Some("06123456789".to_string()));
        assert_eq!(retrieved.role, "family");
    }

    #[test]
    fn test_list_individuals() {
        let conn = setup_db();

        // Create multiple individuals
        let individual1 = Individual::new(
            "Alice Martin".to_string(),
            Some("alice@example.com".to_string()),
            None,
            "family".to_string(),
        );
        let individual2 = Individual::new(
            "Bob Durand".to_string(),
            None,
            Some("06987654321".to_string()),
            "admin".to_string(),
        );
        let individual3 = Individual::new(
            "Charlie Brown".to_string(),
            None,
            None,
            "visitor".to_string(),
        );

        IndividualRepository::create(&conn, &individual1).unwrap();
        IndividualRepository::create(&conn, &individual2).unwrap();
        IndividualRepository::create(&conn, &individual3).unwrap();

        let individuals = IndividualRepository::list(&conn).unwrap();
        assert_eq!(individuals.len(), 3);

        // Verify they are ordered by name
        assert_eq!(individuals[0].name, "Alice Martin");
        assert_eq!(individuals[1].name, "Bob Durand");
        assert_eq!(individuals[2].name, "Charlie Brown");
    }

    #[test]
    fn test_search_individual() {
        let conn = setup_db();

        // Create multiple individuals
        let individual1 = Individual::new(
            "Jean Dupont".to_string(),
            Some("jean.dupont@example.com".to_string()),
            Some("06111111111".to_string()),
            "family".to_string(),
        );
        let individual2 = Individual::new(
            "Marie Dupont".to_string(),
            Some("marie@example.com".to_string()),
            Some("06222222222".to_string()),
            "family".to_string(),
        );
        let individual3 = Individual::new(
            "Pierre Martin".to_string(),
            Some("pierre.martin@example.com".to_string()),
            Some("06333333333".to_string()),
            "admin".to_string(),
        );

        IndividualRepository::create(&conn, &individual1).unwrap();
        IndividualRepository::create(&conn, &individual2).unwrap();
        IndividualRepository::create(&conn, &individual3).unwrap();

        // Search by name
        let results = IndividualRepository::search(&conn, "Dupont").unwrap();
        assert_eq!(results.len(), 2);
        assert!(results.iter().all(|i| i.name.contains("Dupont")));

        // Search by email domain
        let results = IndividualRepository::search(&conn, "example.com").unwrap();
        assert_eq!(results.len(), 3);

        // Search by phone prefix
        let results = IndividualRepository::search(&conn, "06111").unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "Jean Dupont");

        // Search with no results
        let results = IndividualRepository::search(&conn, "NonExistent").unwrap();
        assert_eq!(results.len(), 0);
    }

    #[test]
    fn test_update_individual() {
        let conn = setup_db();

        let individual = Individual::new(
            "Original Name".to_string(),
            Some("original@example.com".to_string()),
            None,
            "family".to_string(),
        );

        let created = IndividualRepository::create(&conn, &individual).unwrap();
        let id = created.id;

        // Update the individual
        let mut updated_individual = Individual::new(
            "Updated Name".to_string(),
            Some("updated@example.com".to_string()),
            Some("06999999999".to_string()),
            "admin".to_string(),
        );
        updated_individual.id = id;

        let updated = IndividualRepository::update(&conn, id, &updated_individual).unwrap();

        assert_eq!(updated.id, id);
        assert_eq!(updated.name, "Updated Name");
        assert_eq!(updated.email, Some("updated@example.com".to_string()));
        assert_eq!(updated.phone, Some("06999999999".to_string()));
        assert_eq!(updated.role, "admin");

        // Verify the update persisted
        let retrieved = IndividualRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.name, "Updated Name");
        assert_eq!(retrieved.email, Some("updated@example.com".to_string()));
    }

    #[test]
    fn test_get_non_existent_individual() {
        let conn = setup_db();

        // Try to get an individual that never existed
        let result = IndividualRepository::get(&conn, 999);
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
    fn test_update_non_existent_individual() {
        let conn = setup_db();

        let individual = Individual::new(
            "Test Name".to_string(),
            Some("test@example.com".to_string()),
            None,
            "family".to_string(),
        );

        // Try to update an individual that never existed
        let result = IndividualRepository::update(&conn, 999, &individual);
        assert!(result.is_err());

        // Verify it's a NotFound error
        match result {
            Err(AppError::NotFound(_)) => (),
            _ => panic!("Should return NotFound error"),
        }
    }
}
