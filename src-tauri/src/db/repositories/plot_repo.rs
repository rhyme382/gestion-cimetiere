use crate::{
    core::models::Plot,
    dto::PlotDTO,
    errors::{AppError, AppResult},
};
use rusqlite::Connection;

pub struct PlotRepository;

impl PlotRepository {
    /// List all plots for a cemetery, ordered by section, row, and number
    pub fn list(conn: &Connection, cemetery_id: i64) -> AppResult<Vec<PlotDTO>> {
        let mut stmt = conn.prepare(
            "SELECT id, cemetery_id, section, row, number, capacity, status, created_at, updated_at FROM plots WHERE cemetery_id = ? ORDER BY section, row, number"
        )?;

        let plots = stmt.query_map([cemetery_id], |row| {
            Ok(PlotDTO {
                id: row.get(0)?,
                cemetery_id: row.get(1)?,
                section: row.get(2)?,
                row: row.get(3)?,
                number: row.get(4)?,
                capacity: row.get(5)?,
                status: row.get(6)?,
                created_at: row.get(7)?,
                updated_at: row.get(8)?,
            })
        })?;

        plots.collect::<Result<Vec<_>, _>>().map_err(AppError::from)
    }

    /// Get a plot by id
    pub fn get(conn: &Connection, id: i64) -> AppResult<PlotDTO> {
        conn.query_row(
            "SELECT id, cemetery_id, section, row, number, capacity, status, created_at, updated_at FROM plots WHERE id = ?",
            [id],
            |row| {
                Ok(PlotDTO {
                    id: row.get(0)?,
                    cemetery_id: row.get(1)?,
                    section: row.get(2)?,
                    row: row.get(3)?,
                    number: row.get(4)?,
                    capacity: row.get(5)?,
                    status: row.get(6)?,
                    created_at: row.get(7)?,
                    updated_at: row.get(8)?,
                })
            }
        ).map_err(|err| {
            match err {
                rusqlite::Error::QueryReturnedNoRows => {
                    AppError::NotFound(format!("Plot with id {} not found", id))
                }
                _ => AppError::Database(err),
            }
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
