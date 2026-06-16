use crate::errors::AppResult;
use rusqlite::Connection;
use std::sync::Mutex;

pub type DbConnection = Mutex<Connection>;

pub fn init_db(db_path: &str) -> AppResult<DbConnection> {
    let conn = Connection::open(db_path)?;

    // Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON", [])?;

    Ok(Mutex::new(conn))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_init_db_in_memory() {
        let db = init_db(":memory:");
        assert!(db.is_ok());
    }

    #[test]
    fn test_foreign_keys_enabled() {
        let db = init_db(":memory:").unwrap();
        let conn = db.lock().unwrap();
        let fk_enabled: bool = conn
            .query_row("PRAGMA foreign_keys", [], |row| row.get(0))
            .unwrap();
        assert!(fk_enabled);
    }
}
