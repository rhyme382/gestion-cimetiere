use rusqlite::Connection;
use crate::{core::models::Cemetery, dto::CemeteryDTO, errors::{AppError, AppResult}};

pub struct CemeteryRepository;

impl CemeteryRepository {
    /// List all cemeteries ordered by creation date (newest first)
    pub fn list(conn: &Connection) -> AppResult<Vec<CemeteryDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, name, commune, capacity, created_at, updated_at FROM cemeteries ORDER BY created_at DESC"
        )?;

        let cemeteries = stmt.query_map([], |row| {
            Ok(CemeteryDTO {
                id: row.get(0)?,
                name: row.get(1)?,
                commune: row.get(2)?,
                capacity: row.get(3)?,
                created_at: row.get(4)?,
                updated_at: row.get(5)?,
            })
        })?;

        let mut result = Vec::new();
        for cemetery in cemeteries {
            result.push(cemetery?);
        }
        Ok(result)
    }

    /// Get a cemetery by id
    pub fn get(conn: &Connection, id: i64) -> AppResult<CemeteryDTO> {
        conn.query_row(
            "SELECT id, name, commune, capacity, created_at, updated_at FROM cemeteries WHERE id = ?",
            [id],
            |row| {
                Ok(CemeteryDTO {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    commune: row.get(2)?,
                    capacity: row.get(3)?,
                    created_at: row.get(4)?,
                    updated_at: row.get(5)?,
                })
            }
        ).map_err(|_| AppError::NotFound(format!("Cemetery with id {} not found", id)))
    }

    /// Create a new cemetery
    pub fn create(conn: &Connection, cemetery: &Cemetery) -> AppResult<CemeteryDTO> {
        conn.execute(
            "INSERT INTO cemeteries (name, commune, capacity, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                &cemetery.name,
                &cemetery.commune,
                cemetery.capacity,
                &cemetery.created_at,
                &cemetery.updated_at,
            ]
        )?;

        let id = conn.last_insert_rowid();
        Self::get(conn, id)
    }

    /// Update a cemetery
    pub fn update(conn: &Connection, id: i64, cemetery: &Cemetery) -> AppResult<CemeteryDTO> {
        // First check if the cemetery exists
        let _existing = Self::get(conn, id)?;

        conn.execute(
            "UPDATE cemeteries SET name = ?, commune = ?, capacity = ?, updated_at = ? WHERE id = ?",
            rusqlite::params![
                &cemetery.name,
                &cemetery.commune,
                cemetery.capacity,
                &cemetery.updated_at,
                id,
            ]
        )?;

        Self::get(conn, id)
    }

    /// Delete a cemetery by id
    pub fn delete(conn: &Connection, id: i64) -> AppResult<bool> {
        let rows_affected = conn.execute(
            "DELETE FROM cemeteries WHERE id = ?",
            [id],
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
        let cemetery3 = Cemetery::new(
            "Cimetière 3".to_string(),
            None,
            None,
        );

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
}
