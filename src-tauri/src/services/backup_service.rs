use chrono::Local;
use std::fs;
use std::path::{Path, PathBuf};

pub struct BackupService;

impl BackupService {
    /// Get backup directory, create if doesn't exist
    fn get_backup_dir() -> Result<PathBuf, String> {
        let backup_dir = PathBuf::from("backups");
        fs::create_dir_all(&backup_dir)
            .map_err(|e| format!("Failed to create backup directory: {}", e))?;
        Ok(backup_dir)
    }

    /// Generate backup filename with timestamp and nanoseconds for uniqueness
    fn get_backup_filename() -> String {
        let now = std::time::SystemTime::now();
        let nanos = now
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos();
        format!(
            "backup_{}_{:09}.db",
            Local::now().format("%Y%m%d_%H%M%S"),
            nanos
        )
    }

    /// Create a backup of the database
    pub fn create_backup(db_path: &str) -> Result<String, String> {
        // Verify source database exists
        if !Path::new(db_path).exists() {
            return Err(format!("Database file not found: {}", db_path));
        }

        // Get backup directory
        let backup_dir = Self::get_backup_dir()?;

        // Generate backup filename
        let backup_filename = Self::get_backup_filename();
        let backup_path = backup_dir.join(&backup_filename);

        // Copy database file
        fs::copy(db_path, &backup_path).map_err(|e| format!("Failed to create backup: {}", e))?;

        Ok(backup_path.to_string_lossy().to_string())
    }

    /// List all available backups
    pub fn list_backups() -> Result<Vec<String>, String> {
        let backup_dir = Self::get_backup_dir()?;

        let entries = fs::read_dir(&backup_dir)
            .map_err(|e| format!("Failed to read backup directory: {}", e))?;

        let mut backups = Vec::new();

        for entry in entries {
            let entry = entry.map_err(|e| format!("Failed to read directory entry: {}", e))?;
            let path = entry.path();

            if path.is_file() && path.extension().map_or(false, |ext| ext == "db") {
                if let Some(filename) = path.file_name() {
                    if let Some(filename_str) = filename.to_str() {
                        backups.push(filename_str.to_string());
                    }
                }
            }
        }

        // Sort by filename (which includes timestamp)
        backups.sort();
        backups.reverse(); // Most recent first

        Ok(backups)
    }

    /// Restore from a backup file
    pub fn restore_backup(backup_filename: &str, db_path: &str) -> Result<(), String> {
        // Validate backup filename to prevent path traversal
        if backup_filename.contains("..") || backup_filename.contains("/") {
            return Err("Invalid backup filename".to_string());
        }

        let backup_dir = Self::get_backup_dir()?;
        let backup_path = backup_dir.join(backup_filename);

        // Verify backup exists
        if !backup_path.exists() {
            return Err(format!("Backup file not found: {}", backup_filename));
        }

        // Validate backup file is actually a SQLite database
        Self::validate_sqlite_file(&backup_path)?;

        // Create backup of current database before restoring
        if Path::new(db_path).exists() {
            let backup_name = format!(
                "backup_pre_restore_{}.db",
                Local::now().format("%Y%m%d_%H%M%S")
            );
            let safety_backup_path = backup_dir.join(&backup_name);
            fs::copy(db_path, &safety_backup_path)
                .map_err(|e| format!("Failed to create safety backup: {}", e))?;
        }

        // Restore from backup
        fs::copy(&backup_path, db_path)
            .map_err(|e| format!("Failed to restore from backup: {}", e))?;

        Ok(())
    }

    /// Validate that a file is a valid SQLite database
    fn validate_sqlite_file(path: &Path) -> Result<(), String> {
        // Read first 16 bytes to check SQLite header
        let content = fs::read(path).map_err(|e| format!("Failed to read backup file: {}", e))?;

        if content.len() < 16 {
            return Err("Backup file is too small, not a valid SQLite database".to_string());
        }

        // SQLite header: "SQLite format 3\x00"
        let sqlite_header = b"SQLite format 3\x00";
        if &content[..16] != sqlite_header {
            return Err("Backup file is not a valid SQLite database".to_string());
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_backup_filename_format() {
        let now = std::time::SystemTime::now();
        let nanos = now
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos();
        let filename = format!(
            "backup_{}_{:09}.db",
            Local::now().format("%Y%m%d_%H%M%S"),
            nanos
        );
        assert!(filename.starts_with("backup_"));
        assert!(filename.ends_with(".db"));
    }

    #[test]
    fn test_validate_sqlite_header() {
        // Create a test file with SQLite header
        let test_path = PathBuf::from("/tmp/test_sqlite.db");
        let mut header = vec![0; 16];
        header[..16].copy_from_slice(b"SQLite format 3\x00");
        fs::write(&test_path, header).unwrap();

        assert!(BackupService::validate_sqlite_file(&test_path).is_ok());

        // Cleanup
        let _ = fs::remove_file(&test_path);
    }
}
