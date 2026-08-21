use crate::{
    core::models::Plot,
    dto::{PlotDTO, HierarchicalPathDTO},
    errors::{AppError, AppResult, NotFoundKind},
};
use rusqlite::Connection;

pub struct PlotRepository;

impl PlotRepository {
    /// List all plots for a cemetery, ordered by section, row, and number, including hierarchy
    pub fn list(conn: &Connection, cemetery_id: i64) -> AppResult<Vec<PlotDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, cemetery_id, section, row, number, capacity, status, administrative_reference, created_at, updated_at FROM plots WHERE cemetery_id = ? ORDER BY section, row, number"
        )?;

        let plot_rows: Vec<(i64, i64, Option<String>, Option<i32>, Option<i32>, i32, String, String, String, String)> = stmt.query_map([cemetery_id], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, i64>(1)?,
                row.get::<_, Option<String>>(2)?,
                row.get::<_, Option<i32>>(3)?,
                row.get::<_, Option<i32>>(4)?,
                row.get::<_, i32>(5)?,
                row.get::<_, String>(6)?,
                row.get::<_, String>(7)?,
                row.get::<_, String>(8)?,
                row.get::<_, String>(9)?,
            ))
        })?.collect::<Result<Vec<_>, _>>()?;

        plot_rows.into_iter().map(|(id, c_id, sec, row_num, num, cap, stat, admin_ref, c_at, u_at)| {
            Ok(PlotDTO {
                id,
                cemetery_id: c_id,
                section: sec,
                row: row_num,
                number: num,
                capacity: cap,
                status: stat,
                administrative_reference: Some(admin_ref),
                hierarchical_path: Self::get_hierarchical_path(conn, id)?,
                created_at: c_at,
                updated_at: u_at,
            })
        }).collect()
    }

    /// Get a plot by id, including its hierarchical path
    pub fn get(conn: &Connection, id: i64) -> AppResult<PlotDTO> {
        conn.query_row(
            "SELECT id, cemetery_id, section, row, number, capacity, status, administrative_reference, created_at, updated_at FROM plots WHERE id = ?",
            [id],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, Option<String>>(2)?,
                    row.get::<_, Option<i32>>(3)?,
                    row.get::<_, Option<i32>>(4)?,
                    row.get::<_, i32>(5)?,
                    row.get::<_, String>(6)?,
                    row.get::<_, String>(7)?,
                    row.get::<_, String>(8)?,
                    row.get::<_, String>(9)?,
                ))
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::with_kind(NotFoundKind::Plot, format!("Plot with id {} not found", id))
                }
                _ => AppError::Database(err),
            }
        }).and_then(|(id, c_id, sec, row_num, num, cap, stat, admin_ref, c_at, u_at)| {
            Ok(PlotDTO {
                id,
                cemetery_id: c_id,
                section: sec,
                row: row_num,
                number: num,
                capacity: cap,
                status: stat,
                administrative_reference: Some(admin_ref),
                hierarchical_path: Self::get_hierarchical_path(conn, id)?,
                created_at: c_at,
                updated_at: u_at,
            })
        })
    }

    /// Create a new plot
    pub fn create(conn: &Connection, plot: &Plot) -> AppResult<PlotDTO> {
        conn.execute(
            "INSERT INTO plots (cemetery_id, section, row, number, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rusqlite::params![
                plot.cemetery_id,
                &plot.section,
                plot.row,
                plot.number,
                plot.capacity,
                &plot.status,
                &plot.created_at,
                &plot.updated_at,
            ]
        )?;

        let id = conn.last_insert_rowid();
        Self::get(conn, id)
    }

    /// Update a plot
    pub fn update(conn: &Connection, id: i64, plot: &Plot) -> AppResult<PlotDTO> {
        // First check if the plot exists
        let _existing = Self::get(conn, id)?;

        conn.execute(
            "UPDATE plots SET cemetery_id = ?, section = ?, row = ?, number = ?, capacity = ?, status = ?, updated_at = ? WHERE id = ?",
            rusqlite::params![
                plot.cemetery_id,
                &plot.section,
                plot.row,
                plot.number,
                plot.capacity,
                &plot.status,
                &plot.updated_at,
                id,
            ]
        )?;

        Self::get(conn, id)
    }

    /// Get the hierarchical path for a plot (section, square, row with identifiers, codes and labels)
    pub fn get_hierarchical_path(conn: &Connection, plot_id: i64) -> AppResult<Option<HierarchicalPathDTO>> {
        let result: Option<(Option<i64>, Option<String>, Option<String>, Option<i64>, Option<String>, Option<String>, Option<i64>, Option<String>, Option<String>)> = conn.query_row(
            "SELECT s.id, s.normalized_code, s.display_label, sq.id, sq.normalized_code, sq.display_label, r.id, r.normalized_code, r.display_label
             FROM plots p
             LEFT JOIN rows r ON p.row_id = r.id
             LEFT JOIN squares sq ON r.square_id = sq.id
             LEFT JOIN sections s ON sq.section_id = s.id
             WHERE p.id = ?",
            [plot_id],
            |row| {
                let has_any = row.get::<_, Option<i64>>(0)?.is_some()
                    || row.get::<_, Option<i64>>(3)?.is_some()
                    || row.get::<_, Option<i64>>(6)?.is_some();

                if has_any {
                    Ok(Some((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                        row.get(5)?,
                        row.get(6)?,
                        row.get(7)?,
                        row.get(8)?,
                    )))
                } else {
                    Ok(None)
                }
            }
        ).or_else(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => Ok(None),
            e => Err(e),
        })?;

        Ok(result.map(|(sec_id, sec_code, sec_label, sq_id, sq_code, sq_label, row_id, row_code, row_label)| {
            HierarchicalPathDTO {
                section_id: sec_id,
                section_code: sec_code,
                section_label: sec_label,
                square_id: sq_id,
                square_code: sq_code,
                square_label: sq_label,
                row_id: row_id,
                row_code: row_code,
                row_label: row_label,
            }
        }))
    }

    /// List all sections in a cemetery
    pub fn list_sections(conn: &Connection, cemetery_id: i64) -> AppResult<Vec<(i64, String, String)>> {
        // Verify cemetery exists
        if !Self::cemetery_exists(conn, cemetery_id)? {
            return Err(AppError::with_kind(
                NotFoundKind::Cemetery,
                format!("Cemetery with id {} not found", cemetery_id),
            ));
        }

        let mut stmt = conn.prepare(
            "SELECT id, normalized_code, display_label FROM sections WHERE cemetery_id = ? AND is_active = 1 ORDER BY display_order, normalized_code"
        )?;

        let sections = stmt.query_map([cemetery_id], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        })?;

        sections.collect::<Result<Vec<_>, _>>().map_err(AppError::from)
    }

    /// List all squares in a section
    pub fn list_squares(conn: &Connection, section_id: i64) -> AppResult<Vec<(i64, String, String)>> {
        // Verify section exists
        let section_exists: i64 = conn.query_row(
            "SELECT COUNT(*) FROM sections WHERE id = ? AND is_active = 1",
            [section_id],
            |row| row.get(0),
        )?;

        if section_exists == 0 {
            return Err(AppError::with_kind(
                NotFoundKind::Section,
                format!("Section with id {} not found", section_id),
            ));
        }

        let mut stmt = conn.prepare(
            "SELECT id, normalized_code, display_label FROM squares WHERE section_id = ? AND is_active = 1 ORDER BY display_order, normalized_code"
        )?;

        let squares = stmt.query_map([section_id], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        })?;

        squares.collect::<Result<Vec<_>, _>>().map_err(AppError::from)
    }

    /// List all rows in a square
    pub fn list_rows(conn: &Connection, square_id: i64) -> AppResult<Vec<(i64, String, String)>> {
        // Verify square exists
        let square_exists: i64 = conn.query_row(
            "SELECT COUNT(*) FROM squares WHERE id = ? AND is_active = 1",
            [square_id],
            |row| row.get(0),
        )?;

        if square_exists == 0 {
            return Err(AppError::with_kind(
                NotFoundKind::Square,
                format!("Square with id {} not found", square_id),
            ));
        }

        let mut stmt = conn.prepare(
            "SELECT id, normalized_code, display_label FROM rows WHERE square_id = ? AND is_active = 1 ORDER BY display_order, normalized_code"
        )?;

        let rows = stmt.query_map([square_id], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        })?;

        rows.collect::<Result<Vec<_>, _>>().map_err(AppError::from)
    }

    /// Get section by id with cemetery validation
    pub fn get_section(conn: &Connection, section_id: i64, cemetery_id: i64) -> AppResult<(i64, String, String)> {
        conn.query_row(
            "SELECT id, normalized_code, display_label FROM sections WHERE id = ? AND cemetery_id = ? AND is_active = 1",
            rusqlite::params![section_id, cemetery_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::with_kind(NotFoundKind::Section, format!("Section with id {} not found in cemetery {}", section_id, cemetery_id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Get square by id with section validation
    pub fn get_square(conn: &Connection, square_id: i64, section_id: i64) -> AppResult<(i64, String, String)> {
        conn.query_row(
            "SELECT id, normalized_code, display_label FROM squares WHERE id = ? AND section_id = ? AND is_active = 1",
            rusqlite::params![square_id, section_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::with_kind(NotFoundKind::Square, format!("Square with id {} not found in section {}", square_id, section_id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Get row by id with square validation
    pub fn get_row(conn: &Connection, row_id: i64, square_id: i64) -> AppResult<(i64, String, String)> {
        conn.query_row(
            "SELECT id, normalized_code, display_label FROM rows WHERE id = ? AND square_id = ? AND is_active = 1",
            rusqlite::params![row_id, square_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::with_kind(NotFoundKind::Row, format!("Row with id {} not found in square {}", row_id, square_id))
                }
                _ => AppError::Database(err),
            }
        })
    }

    /// Verify cemetery exists
    pub fn cemetery_exists(conn: &Connection, cemetery_id: i64) -> AppResult<bool> {
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM cemeteries WHERE id = ?",
            [cemetery_id],
            |row| row.get(0)
        )?;
        Ok(count > 0)
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
    fn test_create_and_get_plot() {
        let conn = setup_db();

        // Create a test cemetery first (foreign key requirement)
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a plot for the cemetery
        let plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(5),
            1,
        );

        let result = PlotRepository::create(&conn, &plot);
        assert!(result.is_ok());

        let created = result.unwrap();
        assert_eq!(created.cemetery_id, created_cemetery.id);
        assert_eq!(created.section, Some("A".to_string()));
        assert_eq!(created.row, Some(1));
        assert_eq!(created.number, Some(5));
        assert_eq!(created.capacity, 1);
        assert_eq!(created.status, "available");
        assert!(created.id > 0);

        // Verify we can get it back
        let retrieved = PlotRepository::get(&conn, created.id).unwrap();
        assert_eq!(retrieved.id, created.id);
        assert_eq!(retrieved.cemetery_id, created_cemetery.id);
        assert_eq!(retrieved.section, Some("A".to_string()));
        assert_eq!(retrieved.row, Some(1));
        assert_eq!(retrieved.number, Some(5));
        assert_eq!(retrieved.capacity, 1);
        assert_eq!(retrieved.status, "available");
    }

    #[test]
    fn test_list_plots() {
        let conn = setup_db();

        // Create a test cemetery
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create plots out of order to verify proper sorting
        // Insert in reverse order: B2, B1, A2, A1
        let plots_to_create = vec![
            Plot::new(
                created_cemetery.id,
                Some("B".to_string()),
                Some(2),
                Some(3),
                1,
            ),
            Plot::new(
                created_cemetery.id,
                Some("B".to_string()),
                Some(1),
                Some(1),
                1,
            ),
            Plot::new(
                created_cemetery.id,
                Some("A".to_string()),
                Some(2),
                Some(2),
                1,
            ),
            Plot::new(
                created_cemetery.id,
                Some("A".to_string()),
                Some(1),
                Some(1),
                1,
            ),
        ];

        for plot in plots_to_create {
            PlotRepository::create(&conn, &plot).unwrap();
        }

        // List plots for the cemetery
        let plots = PlotRepository::list(&conn, created_cemetery.id).unwrap();
        assert_eq!(plots.len(), 4);

        // Verify plots are correctly ordered by section, row, number
        // Expected order: A/1/1, A/2/2, B/1/1, B/2/3
        assert_eq!(plots[0].section, Some("A".to_string()));
        assert_eq!(plots[0].row, Some(1));
        assert_eq!(plots[0].number, Some(1));

        assert_eq!(plots[1].section, Some("A".to_string()));
        assert_eq!(plots[1].row, Some(2));
        assert_eq!(plots[1].number, Some(2));

        assert_eq!(plots[2].section, Some("B".to_string()));
        assert_eq!(plots[2].row, Some(1));
        assert_eq!(plots[2].number, Some(1));

        assert_eq!(plots[3].section, Some("B".to_string()));
        assert_eq!(plots[3].row, Some(2));
        assert_eq!(plots[3].number, Some(3));
    }

    #[test]
    fn test_update_plot() {
        let conn = setup_db();

        // Create a test cemetery
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a plot
        let plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(1),
            1,
        );

        let created = PlotRepository::create(&conn, &plot).unwrap();
        let id = created.id;

        // Update the plot status to occupied
        let mut updated_plot = plot;
        updated_plot.id = id;
        updated_plot.status = "occupied".to_string();
        updated_plot.updated_at = chrono::Utc::now().to_rfc3339();

        let updated = PlotRepository::update(&conn, id, &updated_plot).unwrap();

        assert_eq!(updated.id, id);
        assert_eq!(updated.status, "occupied");

        // Verify the update persisted in the database
        let retrieved = PlotRepository::get(&conn, id).unwrap();
        assert_eq!(retrieved.status, "occupied");
    }

    #[test]
    fn test_get_non_existent_plot() {
        let conn = setup_db();

        // Try to get a plot that never existed
        let result = PlotRepository::get(&conn, 999);
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
    fn test_update_non_existent_plot() {
        let conn = setup_db();

        // Create a test cemetery (needed for valid cemetery_id)
        let cemetery = Cemetery::new(
            "Test Cemetery".to_string(),
            Some("Test City".to_string()),
            Some(500),
        );
        let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

        // Create a plot to use as a template
        let plot = Plot::new(
            created_cemetery.id,
            Some("A".to_string()),
            Some(1),
            Some(1),
            1,
        );

        // Try to update a plot that never existed
        let result = PlotRepository::update(&conn, 999, &plot);
        assert!(result.is_err());

        // Verify it's a NotFound error (from the existence check in update)
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
}
