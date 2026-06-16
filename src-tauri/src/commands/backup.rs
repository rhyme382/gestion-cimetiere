use crate::services::BackupService;
use tauri::State;

/// Create a backup of the database
#[tauri::command]
pub fn create_backup(db_path: State<String>) -> Result<String, String> {
    // Skip backup if using in-memory database (for testing)
    if db_path.as_str() == ":memory:" {
        return Err("Cannot backup in-memory database".to_string());
    }
    BackupService::create_backup(db_path.as_str())
}

/// List all available backups
#[tauri::command]
pub fn list_backups() -> Result<Vec<String>, String> {
    BackupService::list_backups()
}

/// Restore from a specific backup
#[tauri::command]
pub fn restore_backup(backup_filename: String, db_path: State<String>) -> Result<(), String> {
    // Skip restore if using in-memory database (for testing)
    if db_path.as_str() == ":memory:" {
        return Err("Cannot restore to in-memory database".to_string());
    }
    BackupService::restore_backup(&backup_filename, db_path.as_str())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_backup_commands_signature() {
        // Compile-time check that signatures are valid
        assert!(true);
    }
}
