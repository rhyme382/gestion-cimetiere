use crate::{
    core::models::Cemetery,
    dto::CemeteryDTO,
    errors::{AppError, AppResult},
};
use rusqlite::Connection;

pub struct CemeteryRepository;

impl CemeteryRepository {
    /// Normalize cemetery name: trim, lowercase, and compact internal spaces
    fn normalize_name(name: &str) -> String {
        name.trim()
            .to_lowercase()
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ")
    }
    /// List all active cemeteries ordered by creation date (newest first)
    pub fn list(conn: &Connection) -> AppResult<Vec<CemeteryDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, name, commune, capacity, municipality_id, address, is_active, created_at, updated_at
             FROM cemeteries WHERE is_active = 1
             ORDER BY created_at DESC, id DESC"
        )?;

        let cemeteries = stmt.query_map([], |row| {
            Ok(CemeteryDTO {
                id: row.get(0)?,
                name: row.get(1)?,
                commune: row.get(2)?,
                capacity: row.get(3)?,
                municipality_id: row.get(4)?,
                address: row.get(5)?,
                is_active: row.get(6)?,
                created_at: row.get(7)?,
                updated_at: row.get(8)?,
            })
        })?;

        cemeteries
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)
    }

    /// List all cemeteries including inactive ones
    pub fn list_all(conn: &Connection) -> AppResult<Vec<CemeteryDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, name, commune, capacity, municipality_id, address, is_active, created_at, updated_at
             FROM cemeteries
             ORDER BY created_at DESC, id DESC"
        )?;

        let cemeteries = stmt.query_map([], |row| {
            Ok(CemeteryDTO {
                id: row.get(0)?,
                name: row.get(1)?,
                commune: row.get(2)?,
                capacity: row.get(3)?,
                municipality_id: row.get(4)?,
                address: row.get(5)?,
                is_active: row.get(6)?,
                created_at: row.get(7)?,
                updated_at: row.get(8)?,
            })
        })?;

        cemeteries
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)
    }

    /// Get a cemetery by id
    pub fn get(conn: &Connection, id: i64) -> AppResult<CemeteryDTO> {
        conn.query_row(
            "SELECT id, name, commune, capacity, municipality_id, address, is_active, created_at, updated_at
             FROM cemeteries WHERE id = ? AND is_active = 1",
            [id],
            |row| {
                Ok(CemeteryDTO {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    commune: row.get(2)?,
                    capacity: row.get(3)?,
                    municipality_id: row.get(4)?,
                    address: row.get(5)?,
                    is_active: row.get(6)?,
                    created_at: row.get(7)?,
                    updated_at: row.get(8)?,
                })
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Le cimetière avec l'id {} n'existe pas", id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Get a cemetery by id including inactive ones
    pub fn get_all(conn: &Connection, id: i64) -> AppResult<CemeteryDTO> {
        conn.query_row(
            "SELECT id, name, commune, capacity, municipality_id, address, is_active, created_at, updated_at
             FROM cemeteries WHERE id = ?",
            [id],
            |row| {
                Ok(CemeteryDTO {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    commune: row.get(2)?,
                    capacity: row.get(3)?,
                    municipality_id: row.get(4)?,
                    address: row.get(5)?,
                    is_active: row.get(6)?,
                    created_at: row.get(7)?,
                    updated_at: row.get(8)?,
                })
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Le cimetière avec l'id {} n'existe pas", id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Create a new cemetery
    pub fn create(conn: &Connection, cemetery: &Cemetery) -> AppResult<CemeteryDTO> {
        // Validate capacity if provided
        if let Some(capacity) = cemetery.capacity {
            if capacity <= 0 {
                return Err(AppError::InvalidInput(
                    "La capacité doit être positive".to_string(),
                ));
            }
        }

        // Check for normalized name uniqueness among active cemeteries
        let normalized_name = Self::normalize_name(&cemetery.name);
        let mut stmt = conn.prepare("SELECT name FROM cemeteries WHERE is_active = 1")?;

        let existing_names: Vec<String> = stmt
            .query_map([], |row| row.get(0))?
            .collect::<Result<Vec<_>, _>>()?;

        for existing_name in existing_names {
            if Self::normalize_name(&existing_name) == normalized_name {
                return Err(AppError::Duplicate(format!(
                    "Un cimetière actif avec le nom '{}' existe déjà",
                    cemetery.name
                )));
            }
        }

        // Validate municipality_id if provided
        if let Some(municipality_id) = cemetery.municipality_id {
            let exists: Result<i64, _> = conn.query_row(
                "SELECT id FROM municipalities WHERE id = ?",
                [municipality_id],
                |row| row.get(0),
            );
            if exists.is_err() {
                return Err(AppError::InvalidInput(
                    "La commune référencée n'existe pas".to_string(),
                ));
            }
        }

        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, municipality_id, address, is_active, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                &cemetery.name,
                &cemetery.commune,
                cemetery.capacity,
                cemetery.municipality_id,
                &cemetery.address,
                cemetery.is_active,
                &cemetery.created_at,
                &cemetery.updated_at,
            ]
        )?;

        let id = conn.last_insert_rowid();
        Self::get_all(conn, id)
    }

    /// Update a cemetery
    pub fn update(conn: &Connection, id: i64, cemetery: &Cemetery) -> AppResult<CemeteryDTO> {
        // First check if the cemetery exists
        let _existing = Self::get_all(conn, id)?;

        // Validate capacity if provided
        if let Some(capacity) = cemetery.capacity {
            if capacity <= 0 {
                return Err(AppError::InvalidInput(
                    "La capacité doit être positive".to_string(),
                ));
            }
        }

        // Check for normalized name uniqueness among active cemeteries (excluding self)
        let normalized_name = Self::normalize_name(&cemetery.name);
        let mut stmt = conn.prepare("SELECT id, name FROM cemeteries WHERE is_active = 1")?;

        let existing_names: Vec<(i64, String)> = stmt
            .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))?
            .collect::<Result<Vec<_>, _>>()?;

        for (existing_id, existing_name) in existing_names {
            if existing_id != id && Self::normalize_name(&existing_name) == normalized_name {
                return Err(AppError::Duplicate(format!(
                    "Un cimetière actif avec le nom '{}' existe déjà",
                    cemetery.name
                )));
            }
        }

        // Validate municipality_id if provided
        if let Some(municipality_id) = cemetery.municipality_id {
            let exists: Result<i64, _> = conn.query_row(
                "SELECT id FROM municipalities WHERE id = ?",
                [municipality_id],
                |row| row.get(0),
            );
            if exists.is_err() {
                return Err(AppError::InvalidInput(
                    "La commune référencée n'existe pas".to_string(),
                ));
            }
        }

        conn.execute(
            "UPDATE cemeteries SET name = ?, commune = ?, capacity = ?, municipality_id = ?, address = ?, is_active = ?, updated_at = ?
             WHERE id = ?",
            rusqlite::params![
                &cemetery.name,
                &cemetery.commune,
                cemetery.capacity,
                cemetery.municipality_id,
                &cemetery.address,
                cemetery.is_active,
                &cemetery.updated_at,
                id,
            ]
        )?;

        Self::get_all(conn, id)
    }

    /// Soft delete a cemetery (set is_active = 0)
    pub fn delete(conn: &Connection, id: i64) -> AppResult<bool> {
        // Check if cemetery exists
        let _existing = Self::get_all(conn, id)?;

        // Soft delete: set is_active = 0
        let now = chrono::Utc::now().to_rfc3339();
        let rows_affected = conn.execute(
            "UPDATE cemeteries SET is_active = 0, updated_at = ? WHERE id = ?",
            rusqlite::params![&now, id],
        )?;

        Ok(rows_affected > 0)
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
    fn test_create_and_get_cemetery() {
        let conn = setup_db();

        let cemetery = Cemetery::new(
            "Cimetière Central".to_string(),
            Some("Paris".to_string()),
            Some(1000),
        );

        let result = CemeteryRepository::create(&conn, &cemetery);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.name, "Cimetière Central");
        assert_eq!(created.commune, Some("Paris".to_string()));
        assert_eq!(created.capacity, Some(1000));
        assert!(created.id > 0);

        // Verify we can get it back
        let retrieved = CemeteryRepository::get(&conn, created.id).unwrap();
        assert_eq!(retrieved.id, created.id);
        assert_eq!(retrieved.name, created.name);
        assert_eq!(retrieved.commune, created.commune);
        assert_eq!(retrieved.capacity, created.capacity);
    }

    #[test]
    fn test_list_cemeteries() {
        let conn = setup_db();

        // Create three cemeteries
        let cemetery1 = Cemetery::new(
            "Cimetière 1".to_string(),
            Some("Paris".to_string()),
            Some(100),
        );
        let cemetery2 = Cemetery::new(
            "Cimetière 2".to_string(),
            Some("Lyon".to_string()),
            Some(200),
        );
        let cemetery3 = Cemetery::new("Cimetière 3".to_string(), None, None);

        CemeteryRepository::create(&conn, &cemetery1).unwrap();
        CemeteryRepository::create(&conn, &cemetery2).unwrap();
        CemeteryRepository::create(&conn, &cemetery3).unwrap();

        let cemeteries = CemeteryRepository::list(&conn).unwrap();
        assert_eq!(cemeteries.len(), 3);

        // Verify they are ordered by created_at DESC (most recent first)
        assert_eq!(cemeteries[0].name, "Cimetière 3");
        assert_eq!(cemeteries[1].name, "Cimetière 2");
        assert_eq!(cemeteries[2].name, "Cimetière 1");
    }

    #[test]
    fn test_update_cemetery() {
        let conn = setup_db();

        let cemetery = Cemetery::new(
            "Original Name".to_string(),
            Some("Original City".to_string()),
            Some(500),
        );

        let created = CemeteryRepository::create(&conn, &cemetery).unwrap();
        let id = created.id;

        // Update the cemetery
        let mut updated_cemetery = Cemetery::new(
            "Updated Name".to_string(),
            Some("Updated City".to_string()),
            Some(750),
        );
        updated_cemetery.id = id;

        let updated = CemeteryRepository::update(&conn, id, &updated_cemetery).unwrap();

        assert_eq!(updated.id, id);
        assert_eq!(updated.name, "Updated Name");
        assert_eq!(updated.commune, Some("Updated City".to_string()));
        assert_eq!(updated.capacity, Some(750));

        // Verify the update persisted
        let retrieved = CemeteryRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.name, "Updated Name");
        assert_eq!(retrieved.commune, Some("Updated City".to_string()));
        assert_eq!(retrieved.capacity, Some(750));
    }

    #[test]
    fn test_delete_cemetery() {
        let conn = setup_db();

        let cemetery = Cemetery::new(
            "To Delete".to_string(),
            Some("Some City".to_string()),
            Some(100),
        );

        let created = CemeteryRepository::create(&conn, &cemetery).unwrap();
        let id = created.id;

        // Verify it exists
        let result = CemeteryRepository::get(&conn, id);
        assert!(result.is_ok());

        // Delete it
        let deleted = CemeteryRepository::delete(&conn, id).unwrap();
        assert!(deleted);

        // Verify it no longer exists
        let result = CemeteryRepository::get(&conn, id);
        assert!(result.is_err());
        match result {
            Err(AppError::NotFound(_)) => (),
            _ => panic!("Expected NotFound error"),
        }
    }

    #[test]
    fn test_get_non_existent_cemetery() {
        let conn = setup_db();

        // Try to get a cemetery that never existed
        let result = CemeteryRepository::get(&conn, 999);
        assert!(result.is_err());

        // Verify it's a NotFound error, not a Database error
        match result {
            Err(AppError::NotFound(msg)) => {
                assert!(msg.contains("999"));
            }
            Err(AppError::Database(_)) => {
                panic!("Should return NotFound, not Database error");
            }
            Err(AppError::InvalidInput(_))
            | Err(AppError::Internal(_))
            | Err(AppError::Duplicate(_)) => {
                panic!("Should return NotFound, not other error variant");
            }
            Ok(_) => panic!("Should return an error"),
        }
    }

    #[test]
    fn test_cemetery_name_normalization_spaces() {
        let conn = setup_db();

        // Create cemetery with multiple spaces
        let cemetery1 = Cemetery::new(
            "Cimetière   Central".to_string(), // Multiple spaces
            Some("Paris".to_string()),
            Some(1000),
        );

        let result1 = CemeteryRepository::create(&conn, &cemetery1);
        assert!(result1.is_ok());

        // Try to create another with single spaces (should be duplicate)
        let cemetery2 = Cemetery::new(
            "Cimetière Central".to_string(), // Single space (normalized same as above)
            Some("Paris".to_string()),
            Some(1000),
        );

        let result2 = CemeteryRepository::create(&conn, &cemetery2);
        assert!(result2.is_err());
        match result2 {
            Err(AppError::Duplicate(msg)) => {
                assert!(msg.contains("Cimetière Central"));
            }
            _ => panic!("Expected Duplicate error"),
        }
    }

    #[test]
    fn test_cemetery_name_normalization_case() {
        let conn = setup_db();

        // Create cemetery with uppercase
        let cemetery1 = Cemetery::new(
            "CENTRAL Cemetery".to_string(),
            Some("City".to_string()),
            Some(500),
        );

        let result1 = CemeteryRepository::create(&conn, &cemetery1);
        assert!(result1.is_ok());

        // Try to create another with lowercase (should be duplicate)
        let cemetery2 = Cemetery::new(
            "central cemetery".to_string(), // Lowercase (normalized same)
            Some("City".to_string()),
            Some(500),
        );

        let result2 = CemeteryRepository::create(&conn, &cemetery2);
        assert!(result2.is_err());
        match result2 {
            Err(AppError::Duplicate(_)) => (),
            _ => panic!("Expected Duplicate error"),
        }
    }

    #[test]
    fn test_cemetery_inactive_not_checked_for_uniqueness() {
        let conn = setup_db();

        // Create cemetery
        let cemetery1 = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("City".to_string()),
            Some(500),
        );

        let created = CemeteryRepository::create(&conn, &cemetery1).unwrap();
        let id = created.id;

        // Soft delete it
        CemeteryRepository::delete(&conn, id).unwrap();

        // Should be able to create another with same name since first is inactive
        let cemetery2 = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("City".to_string()),
            Some(500),
        );

        let result2 = CemeteryRepository::create(&conn, &cemetery2);
        assert!(result2.is_ok());
    }
}
