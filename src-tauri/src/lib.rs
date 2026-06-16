pub mod core;
pub mod db;
pub mod dto;
pub mod errors;
pub mod commands;
pub mod services;

pub fn init_app() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize database at app startup
    let db_path = if cfg!(debug_assertions) {
        ":memory:"
    } else {
        "gestion_cimetiere.db"
    };

    let conn = db::init_db(db_path)?;
    let lock = conn.lock().unwrap();
    db::run_migrations(&lock)?;
    drop(lock);

    Ok(())
}

#[cfg(debug_assertions)]
pub fn export_bindings() -> Result<(), Box<dyn std::error::Error>> {
    // Type generation handled via build script
    // See build.rs for details
    Ok(())
}
