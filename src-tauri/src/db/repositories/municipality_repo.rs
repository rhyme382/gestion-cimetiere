use crate::{
    core::models::Municipality,
    dto::MunicipalityDTO,
    errors::{AppError, AppResult},
};
use rusqlite::Connection;

pub struct MunicipalityRepository;

impl MunicipalityRepository {
    /// Check if a configured municipality (gestionnaire) already exists
    /// A gestionnaire is a municipality with a valid INSEE code (not the placeholder '00000')
    /// Placeholder '00000' is used during migration for backward compatibility with old data
    fn has_configured_municipality(conn: &Connection) -> AppResult<bool> {
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM municipalities WHERE insee_code IS NOT NULL AND TRIM(insee_code) != '' AND insee_code != '00000'",
            [],
            |row| row.get(0),
        )?;
        Ok(count > 0)
    }

    /// Validate INSEE code: must be exactly 5 alphanumeric characters
    /// Returns the normalized (uppercase) INSEE code
    pub fn validate_insee_code(code: &str) -> AppResult<String> {
        let normalized = code.trim().to_uppercase();
        if normalized.len() != 5 {
            return Err(AppError::InvalidInput(
                "Le code INSEE doit contenir exactement 5 caractères".to_string(),
            ));
        }
        if !normalized.chars().all(|c| c.is_alphanumeric()) {
            return Err(AppError::InvalidInput(
                "Le code INSEE ne doit contenir que des caractères alphanumériques".to_string(),
            ));
        }
        Ok(normalized)
    }

    /// Validate email format (basic check)
    pub fn validate_email(email: &str) -> AppResult<()> {
        let trimmed = email.trim();
        if !trimmed.contains('@') || !trimmed.contains('.') {
            return Err(AppError::InvalidInput(
                "L'adresse e-mail n'est pas valide".to_string(),
            ));
        }
        Ok(())
    }

    /// List municipalities configured as gestionnaire (with valid INSEE code, excluding placeholder '00000')
    /// Returns at most one municipality (the unique gestionnaire)
    /// Placeholder '00000' is reserved for legacy data compatibility (migration 0010 backfill)
    pub fn list(conn: &Connection) -> AppResult<Vec<MunicipalityDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, name, insee_code, postal_code, email, department, region, notes, created_at, updated_at
             FROM municipalities
             WHERE insee_code IS NOT NULL AND TRIM(insee_code) != '' AND insee_code != '00000'
             ORDER BY created_at DESC, id DESC
             LIMIT 1"
        )?;

        let municipalities = stmt.query_map([], |row| {
            Ok(MunicipalityDTO {
                id: row.get(0)?,
                name: row.get(1)?,
                insee_code: row.get(2)?,
                postal_code: row.get(3)?,
                email: row.get(4)?,
                department: row.get(5)?,
                region: row.get(6)?,
                notes: row.get(7)?,
                created_at: row.get(8)?,
                updated_at: row.get(9)?,
            })
        })?;

        municipalities
            .collect::<Result<Vec<_>, _>>()
            .map_err(AppError::from)
    }

    /// Get a municipality by id
    pub fn get(conn: &Connection, id: i64) -> AppResult<MunicipalityDTO> {
        conn.query_row(
            "SELECT id, name, insee_code, postal_code, email, department, region, notes, created_at, updated_at
             FROM municipalities WHERE id = ?",
            [id],
            |row| {
                Ok(MunicipalityDTO {
                    id: row.get(0)?,
                    name: row.get(1)?,
                    insee_code: row.get(2)?,
                    postal_code: row.get(3)?,
                    email: row.get(4)?,
                    department: row.get(5)?,
                    region: row.get(6)?,
                    notes: row.get(7)?,
                    created_at: row.get(8)?,
                    updated_at: row.get(9)?,
                })
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("La commune avec l'id {} n'existe pas", id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Create a new municipality with full validation
    /// Only one gestionnaire municipality (with valid INSEE code) is allowed
    pub fn create(conn: &Connection, municipality: &Municipality) -> AppResult<MunicipalityDTO> {
        // Validate and normalize INSEE code
        let normalized_insee = Self::validate_insee_code(&municipality.insee_code)?;

        // Validate email if provided
        if let Some(email) = &municipality.email {
            if !email.is_empty() {
                Self::validate_email(email)?;
            }
        }

        // Check if a configured gestionnaire already exists
        if Self::has_configured_municipality(conn)? {
            return Err(AppError::Duplicate(
                "Une commune gestionnaire est déjà configurée. Une seule commune gestionnaire est autorisée".to_string(),
            ));
        }

        // Check for INSEE code uniqueness
        let existing_insee: Result<i64, _> = conn.query_row(
            "SELECT id FROM municipalities WHERE insee_code = ?",
            [&normalized_insee],
            |row| row.get(0),
        );

        if existing_insee.is_ok() {
            return Err(AppError::Duplicate(format!(
                "Une commune avec le code INSEE {} existe déjà",
                normalized_insee
            )));
        }

        // Check for name uniqueness among configured municipalities
        let existing_name: Result<i64, _> = conn.query_row(
            "SELECT id FROM municipalities WHERE name = ? AND insee_code IS NOT NULL AND TRIM(insee_code) != ''",
            [&municipality.name],
            |row| row.get(0),
        );

        if existing_name.is_ok() {
            return Err(AppError::Duplicate(format!(
                "Une commune avec le nom {} existe déjà",
                municipality.name
            )));
        }

        conn.execute(
            "INSERT INTO municipalities (name, insee_code, postal_code, email, department, region, notes, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                &municipality.name,
                &normalized_insee,
                &municipality.postal_code,
                &municipality.email,
                &municipality.department,
                &municipality.region,
                &municipality.notes,
                &municipality.created_at,
                &municipality.updated_at,
            ]
        )?;

        let id = conn.last_insert_rowid();
        Self::get(conn, id)
    }

    /// Update a municipality with validation
    pub fn update(
        conn: &Connection,
        id: i64,
        municipality: &Municipality,
    ) -> AppResult<MunicipalityDTO> {
        // Verify municipality exists
        let _existing = Self::get(conn, id)?;

        // Validate and normalize INSEE code
        let normalized_insee = Self::validate_insee_code(&municipality.insee_code)?;

        // Validate email if provided
        if let Some(email) = &municipality.email {
            if !email.is_empty() {
                Self::validate_email(email)?;
            }
        }

        // Check for INSEE code uniqueness (excluding self)
        let existing_insee: Result<i64, _> = conn.query_row(
            "SELECT id FROM municipalities WHERE insee_code = ? AND id != ?",
            rusqlite::params![&normalized_insee, id],
            |row| row.get(0),
        );

        if existing_insee.is_ok() {
            return Err(AppError::Duplicate(format!(
                "Une commune avec le code INSEE {} existe déjà",
                normalized_insee
            )));
        }

        // Check for name uniqueness (excluding self)
        let existing_name: Result<i64, _> = conn.query_row(
            "SELECT id FROM municipalities WHERE name = ? AND id != ?",
            rusqlite::params![&municipality.name, id],
            |row| row.get(0),
        );

        if existing_name.is_ok() {
            return Err(AppError::Duplicate(format!(
                "Une commune avec le nom {} existe déjà",
                municipality.name
            )));
        }

        conn.execute(
            "UPDATE municipalities SET name = ?, insee_code = ?, postal_code = ?, email = ?, department = ?, region = ?, notes = ?, updated_at = ? WHERE id = ?",
            rusqlite::params![
                &municipality.name,
                &normalized_insee,
                &municipality.postal_code,
                &municipality.email,
                &municipality.department,
                &municipality.region,
                &municipality.notes,
                &municipality.updated_at,
                id,
            ]
        )?;

        Self::get(conn, id)
    }

    /// Delete a municipality by id
    /// Gestionnaire municipalities (with valid INSEE code) cannot be deleted
    pub fn delete(conn: &Connection, id: i64) -> AppResult<()> {
        // Verify municipality exists first
        let existing = Self::get(conn, id)?;

        // Check if this is the configured gestionnaire
        if !existing.insee_code.is_empty() {
            return Err(AppError::Internal(
                "Impossible de supprimer la commune gestionnaire configurée".to_string(),
            ));
        }

        // Check if municipality is referenced by any cemeteries
        let cemetery_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM cemeteries WHERE municipality_id = ?",
            [id],
            |row| row.get(0),
        )?;

        if cemetery_count > 0 {
            return Err(AppError::Internal(
                "Impossible de supprimer une commune qui est référencée par des cimetières"
                    .to_string(),
            ));
        }

        conn.execute("DELETE FROM municipalities WHERE id = ?", [id])?;
        Ok(())
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
    fn test_create_municipality_success() {
        let conn = setup_db();

        let municipality = Municipality::new(
            "Paris".to_string(),
            "75056".to_string(),
            Some("75000".to_string()),
            Some("contact@paris.fr".to_string()),
        );

        let result = MunicipalityRepository::create(&conn, &municipality);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.name, "Paris");
        assert_eq!(created.insee_code, "75056"); // Normalized to uppercase
        assert_eq!(created.postal_code, Some("75000".to_string()));
        assert_eq!(created.email, Some("contact@paris.fr".to_string()));
        assert!(created.id > 0);
    }

    #[test]
    fn test_insee_code_uppercase_normalization() {
        let conn = setup_db();

        let municipality = Municipality::new(
            "Test City".to_string(),
            "abc12".to_string(), // Lowercase
            None,
            None,
        );

        let result = MunicipalityRepository::create(&conn, &municipality);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.insee_code, "ABC12"); // Should be normalized to uppercase

        // Verify we cannot create a second gestionnaire
        let municipality2 = Municipality::new(
            "Another".to_string(),
            "xyz34".to_string(), // Different INSEE
            None,
            None,
        );

        let result2 = MunicipalityRepository::create(&conn, &municipality2);
        assert!(result2.is_err());
        match result2 {
            Err(AppError::Duplicate(msg)) => {
                assert!(msg.contains("commune gestionnaire est déjà configurée")); // Only one gestionnaire
            }
            _ => panic!("Expected Duplicate error for second gestionnaire"),
        }
    }

    #[test]
    fn test_insee_code_validation_length() {
        let conn = setup_db();

        let municipality = Municipality::new(
            "Test City".to_string(),
            "123".to_string(), // Too short
            None,
            None,
        );

        let result = MunicipalityRepository::create(&conn, &municipality);
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("exactement 5 caractères"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[test]
    fn test_insee_code_validation_alphanumeric() {
        let conn = setup_db();

        let municipality = Municipality::new(
            "Test City".to_string(),
            "75@56".to_string(), // Invalid character
            None,
            None,
        );

        let result = MunicipalityRepository::create(&conn, &municipality);
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("alphanumériques"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[test]
    fn test_email_validation() {
        let conn = setup_db();

        let municipality = Municipality::new(
            "Test City".to_string(),
            "12345".to_string(),
            None,
            Some("invalid-email".to_string()),
        );

        let result = MunicipalityRepository::create(&conn, &municipality);
        assert!(result.is_err());
        match result {
            Err(AppError::InvalidInput(msg)) => {
                assert!(msg.contains("adresse e-mail"));
            }
            _ => panic!("Expected InvalidInput error"),
        }
    }

    #[test]
    fn test_duplicate_insee_code() {
        let conn = setup_db();

        let municipality1 =
            Municipality::new("City One".to_string(), "12345".to_string(), None, None);

        let municipality2 = Municipality::new(
            "City Two".to_string(),
            "54321".to_string(), // Different INSEE code
            None,
            None,
        );

        let result1 = MunicipalityRepository::create(&conn, &municipality1);
        assert!(result1.is_ok());

        // Attempting to create a second gestionnaire should fail
        let result2 = MunicipalityRepository::create(&conn, &municipality2);
        assert!(result2.is_err());
        match result2 {
            Err(AppError::Duplicate(msg)) => {
                assert!(msg.contains("commune gestionnaire est déjà configurée"));
            }
            _ => panic!("Expected Duplicate error for second gestionnaire"),
        }
    }

    #[test]
    fn test_duplicate_name() {
        let conn = setup_db();

        let municipality1 =
            Municipality::new("Same Name".to_string(), "12345".to_string(), None, None);

        let municipality2 = Municipality::new(
            "Same Name".to_string(), // Duplicate name
            "54321".to_string(),
            None,
            None,
        );

        let result1 = MunicipalityRepository::create(&conn, &municipality1);
        assert!(result1.is_ok());

        // Attempting to create a second gestionnaire should fail
        let result2 = MunicipalityRepository::create(&conn, &municipality2);
        assert!(result2.is_err());
        match result2 {
            Err(AppError::Duplicate(msg)) => {
                assert!(msg.contains("commune gestionnaire est déjà configurée"));
            }
            _ => panic!("Expected Duplicate error for second gestionnaire"),
        }
    }

    #[test]
    fn test_update_municipality() {
        let conn = setup_db();

        let municipality =
            Municipality::new("Original Name".to_string(), "12345".to_string(), None, None);

        let created = MunicipalityRepository::create(&conn, &municipality).unwrap();
        let id = created.id;

        let mut updated = Municipality::new(
            "Updated Name".to_string(),
            "54321".to_string(),
            Some("75000".to_string()),
            None,
        );
        updated.id = id;
        updated.created_at = created.created_at;

        let result = MunicipalityRepository::update(&conn, id, &updated);
        assert!(result.is_ok());

        let updated_dto = result.unwrap();
        assert_eq!(updated_dto.name, "Updated Name");
        assert_eq!(updated_dto.insee_code, "54321");
        assert_eq!(updated_dto.postal_code, Some("75000".to_string()));
    }

    #[test]
    fn test_list_municipalities() {
        let conn = setup_db();

        let m1 = Municipality::new("City 1".to_string(), "11111".to_string(), None, None);

        let created = MunicipalityRepository::create(&conn, &m1).unwrap();

        // List should return only the configured gestionnaire (or empty if none)
        let list = MunicipalityRepository::list(&conn).unwrap();
        assert_eq!(list.len(), 1, "List should return exactly one gestionnaire");
        assert_eq!(list[0].name, "City 1");
        assert_eq!(list[0].id, created.id);
    }

    #[test]
    fn test_get_municipality_not_found() {
        let conn = setup_db();
        let result = MunicipalityRepository::get(&conn, 999);
        assert!(result.is_err());
        match result {
            Err(AppError::NotFound(msg)) => {
                assert!(msg.contains("999"));
            }
            _ => panic!("Expected NotFound error"),
        }
    }

    #[test]
    fn test_municipality_persistence() {
        // Create and populate a database
        let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
        conn.execute("PRAGMA foreign_keys = ON", [])
            .expect("Failed to enable foreign keys");
        crate::db::migrations::run_migrations(&conn).expect("Failed to run migrations");

        let municipality = Municipality::new(
            "Lyon".to_string(),
            "69123".to_string(),
            Some("69000".to_string()),
            Some("contact@lyon.fr".to_string()),
        );

        let created = MunicipalityRepository::create(&conn, &municipality).unwrap();
        let id = created.id;
        let created_at = created.created_at.clone();
        let updated_at = created.updated_at.clone();

        // Retrieve immediately after creation
        let retrieved = MunicipalityRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.name, "Lyon");
        assert_eq!(retrieved.insee_code, "69123");
        assert_eq!(retrieved.postal_code, Some("69000".to_string()));
        assert_eq!(retrieved.email, Some("contact@lyon.fr".to_string()));
        assert_eq!(retrieved.created_at, created_at);
        assert_eq!(retrieved.updated_at, updated_at);

        // Retrieve again to ensure data persists
        let retrieved_again = MunicipalityRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved_again.insee_code, "69123");
        assert_eq!(retrieved_again.name, "Lyon");
    }

    #[test]
    fn test_singleton_gestionnaire_cannot_be_deleted() {
        let conn = setup_db();

        let municipality = Municipality::new(
            "Test City".to_string(),
            "12345".to_string(),
            None,
            None,
        );

        let created = MunicipalityRepository::create(&conn, &municipality).unwrap();
        let id = created.id;

        // Attempting to delete the gestionnaire should fail
        let result = MunicipalityRepository::delete(&conn, id);
        assert!(result.is_err());
        match result {
            Err(AppError::Internal(msg)) => {
                assert!(msg.contains("commune gestionnaire"));
            }
            _ => panic!("Expected Internal error for deleting gestionnaire"),
        }

        // Verify municipality still exists
        let retrieved = MunicipalityRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.name, "Test City");
    }

    #[test]
    fn test_list_empty_when_no_gestionnaire() {
        let conn = setup_db();

        // List should be empty when no gestionnaire exists
        let list = MunicipalityRepository::list(&conn).unwrap();
        assert_eq!(list.len(), 0);
    }

    #[test]
    fn test_get_by_id_bypasses_gestionnaire_filter() {
        let conn = setup_db();

        let municipality = Municipality::new(
            "Test City".to_string(),
            "12345".to_string(),
            None,
            None,
        );

        let created = MunicipalityRepository::create(&conn, &municipality).unwrap();
        let id = created.id;

        // Get should work for the gestionnaire
        let retrieved = MunicipalityRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.id, id);
        assert_eq!(retrieved.name, "Test City");
    }

    #[test]
    fn test_compatibility_placeholder_00000_not_counted_as_gestionnaire() {
        // Simulate legacy data backfilled with placeholder '00000' (migration 0010 compatibility)
        let conn = setup_db();

        // Manually insert legacy municipalities with placeholder INSEE code (as done in migration 0010)
        conn.execute(
            "INSERT INTO municipalities (name, insee_code, postal_code, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![
                "Legacy Municipality",
                "00000", // Placeholder from migration backfill
                Some("13000".to_string()),
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z"
            ],
        )
        .unwrap();

        // Verify legacy municipality exists but is not counted as a configured gestionnaire
        let list = MunicipalityRepository::list(&conn).unwrap();
        assert_eq!(
            list.len(),
            0,
            "Legacy municipalities with placeholder '00000' should not appear in gestionnaire list"
        );

        // Verify we can still get it by ID
        let legacy = MunicipalityRepository::get(&conn, 1).unwrap();
        assert_eq!(legacy.name, "Legacy Municipality");
        assert_eq!(legacy.insee_code, "00000");

        // Now create a REAL gestionnaire with a valid INSEE code
        let municipality = Municipality::new(
            "Real Municipality".to_string(),
            "75056".to_string(),
            Some("75000".to_string()),
            None,
        );

        let created = MunicipalityRepository::create(&conn, &municipality).unwrap();
        assert_eq!(created.name, "Real Municipality");
        assert_eq!(created.insee_code, "75056");

        // Now list should return only the real gestionnaire
        let list_after = MunicipalityRepository::list(&conn).unwrap();
        assert_eq!(
            list_after.len(),
            1,
            "List should return exactly the real gestionnaire"
        );
        assert_eq!(list_after[0].name, "Real Municipality");

        // Verify that a second real gestionnaire is refused
        let municipality2 = Municipality::new(
            "Another".to_string(),
            "69123".to_string(),
            None,
            None,
        );

        let result = MunicipalityRepository::create(&conn, &municipality2);
        assert!(result.is_err());
        match result {
            Err(AppError::Duplicate(msg)) => {
                assert!(msg.contains("commune gestionnaire est déjà configurée"));
            }
            _ => panic!("Expected Duplicate error"),
        }
    }
}
