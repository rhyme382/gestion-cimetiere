use gestion_cimetiere::services::BackupService;
use std::fs;
use std::path::Path;
use tempfile::TempDir;

#[test]
fn test_backup_creation() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");

    // Create a test database file
    let sqlite_header = b"SQLite format 3\x00";
    let mut content = vec![0; 1024];
    content[..16].copy_from_slice(sqlite_header);
    fs::write(&test_db, &content).expect("Failed to create test DB");

    // Create backup
    let result = BackupService::create_backup(test_db.to_str().unwrap());
    assert!(result.is_ok(), "Backup creation failed");

    let backup_path = result.unwrap();
    assert!(
        backup_path.ends_with(".db"),
        "Backup should have .db extension"
    );
    assert!(Path::new(&backup_path).exists(), "Backup file should exist");
}

#[test]
fn test_backup_nonexistent_db() {
    let temp_dir = TempDir::new().unwrap();
    let nonexistent_db = temp_dir.path().join("nonexistent.db");

    let result = BackupService::create_backup(nonexistent_db.to_str().unwrap());
    assert!(result.is_err(), "Should fail when DB doesn't exist");
}

#[test]
fn test_list_backups_empty() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");

    let result = BackupService::list_backups(test_db.to_str().unwrap());
    assert!(result.is_ok(), "list_backups should not fail");
    let backups = result.unwrap();
    assert_eq!(backups.len(), 0, "Should have no backups initially");
}

#[test]
fn test_list_backups_multiple() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");

    // Create test database
    let sqlite_header = b"SQLite format 3\x00";
    let mut content = vec![0; 1024];
    content[..16].copy_from_slice(sqlite_header);
    fs::write(&test_db, &content).expect("Failed to create test DB");

    // Create multiple backups
    let backup1 = BackupService::create_backup(test_db.to_str().unwrap());
    assert!(backup1.is_ok());

    let backup2 = BackupService::create_backup(test_db.to_str().unwrap());
    assert!(backup2.is_ok());

    // List backups
    let result = BackupService::list_backups(test_db.to_str().unwrap());
    assert!(result.is_ok());
    let backups = result.unwrap();
    assert_eq!(backups.len(), 2, "Should have 2 backups");
}

#[test]
fn test_restore_backup() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");
    let backup_filename: String;

    // Create initial database
    let sqlite_header = b"SQLite format 3\x00";
    let mut initial_content = vec![0; 1024];
    initial_content[..16].copy_from_slice(sqlite_header);
    initial_content[1023] = 42; // Mark with distinctive byte
    fs::write(&test_db, &initial_content).expect("Failed to create initial DB");

    // Create backup
    let result = BackupService::create_backup(test_db.to_str().unwrap());
    assert!(result.is_ok(), "Backup creation failed");
    let backup_path = result.unwrap();
    backup_filename = Path::new(&backup_path)
        .file_name()
        .unwrap()
        .to_str()
        .unwrap()
        .to_string();

    // Modify database
    let mut modified_content = vec![0; 1024];
    modified_content[..16].copy_from_slice(sqlite_header);
    modified_content[1023] = 99; // Different marker
    fs::write(&test_db, &modified_content).expect("Failed to modify DB");

    // Verify modification
    let current = fs::read(&test_db).unwrap();
    assert_eq!(current[1023], 99, "DB should be modified");

    // Restore from backup
    let restore_result = BackupService::restore_backup(&backup_filename, test_db.to_str().unwrap());
    assert!(restore_result.is_ok(), "Restore should succeed");

    // Verify restoration
    let restored = fs::read(&test_db).unwrap();
    assert_eq!(
        restored[1023], 42,
        "DB should be restored to original state"
    );
}

#[test]
fn test_restore_invalid_backup() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");

    // Try to restore nonexistent backup
    let result = BackupService::restore_backup("nonexistent_backup.db", test_db.to_str().unwrap());
    assert!(result.is_err(), "Should fail for nonexistent backup");
}

#[test]
fn test_restore_invalid_sqlite_file() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");

    // Create test database
    let sqlite_header = b"SQLite format 3\x00";
    let mut content = vec![0; 1024];
    content[..16].copy_from_slice(sqlite_header);
    fs::write(&test_db, &content).expect("Failed to create test DB");

    // Create backup
    let backup_result = BackupService::create_backup(test_db.to_str().unwrap());
    assert!(backup_result.is_ok());
    let backup_path = backup_result.unwrap();
    let backup_filename = Path::new(&backup_path)
        .file_name()
        .unwrap()
        .to_str()
        .unwrap()
        .to_string();

    // Create invalid backup file (overwrite the backup with non-SQLite data)
    let backup_dir = temp_dir.path().join("backups");
    let invalid_path = backup_dir.join(&backup_filename);
    fs::write(&invalid_path, b"This is not a SQLite database").unwrap();

    // Try to restore invalid backup
    let restore_result = BackupService::restore_backup(&backup_filename, test_db.to_str().unwrap());
    assert!(
        restore_result.is_err(),
        "Should fail for invalid SQLite file"
    );
}

#[test]
fn test_path_traversal_prevention() {
    let temp_dir = TempDir::new().unwrap();
    let test_db = temp_dir.path().join("test.db");

    // Try path traversal attack
    let result = BackupService::restore_backup("../../../etc/passwd", test_db.to_str().unwrap());
    assert!(result.is_err(), "Should prevent path traversal");

    // Try with forward slash
    let result2 = BackupService::restore_backup("/etc/passwd", test_db.to_str().unwrap());
    assert!(result2.is_err(), "Should prevent absolute paths");
}
