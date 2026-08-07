use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{
    BurialRepository, CemeteryRepository, ConcessionRepository, PlotRepository,
};
use gestion_cimetiere::services::PdfService;
use rusqlite::Connection;
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

fn setup_test_db() -> Connection {
    let conn = Connection::open_in_memory().expect("Failed to open in-memory database");

    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");

    run_migrations(&conn).expect("Failed to run migrations");

    conn
}

fn get_unique_test_dir() -> String {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("/tmp/test_mvp18_pdf_{}", timestamp)
}

fn verify_pdf_file(path: &str) -> Result<(), String> {
    // Check file exists
    if !Path::new(path).exists() {
        return Err(format!("PDF file does not exist: {}", path));
    }

    // Check file has .pdf extension
    if !path.ends_with(".pdf") {
        return Err(format!("File does not have .pdf extension: {}", path));
    }

    // Read file and verify size > 0
    let content = fs::read(path).map_err(|e| format!("Failed to read PDF file: {}", e))?;

    if content.is_empty() {
        return Err("PDF file is empty".to_string());
    }

    // Verify PDF header
    if !content.starts_with(b"%PDF") {
        return Err(format!(
            "File does not start with PDF header. Got: {:?}",
            &content[..4.min(content.len())]
        ));
    }

    Ok(())
}

#[test]
fn test_integration_pdf_generation_basic() {
    let conn = setup_test_db();

    // Setup: create cemetery and plot
    conn.execute(
        "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
        rusqlite::params![
            "Test Cemetery",
            "2026-06-16 10:00:00",
            "2026-06-16 10:00:00"
        ],
    )
    .unwrap();

    conn.execute(
        "INSERT INTO plots (cemetery_id, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 10, "available", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO concessions (cemetery_id, plot_id, concession_type, start_date, duration_years, expires_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rusqlite::params![
            1,
            1,
            "PERPETUELLE",
            "2026-06-16",
            Option::<i32>::None,
            Option::<String>::None,
            "PERPETUELLE",
            "2026-06-16T00:00:00Z",
            "2026-06-16T00:00:00Z"
        ],
    ).unwrap();

    // Fetch data and generate PDF
    let concession = ConcessionRepository::get(&conn, 1).unwrap();
    let cemetery = CemeteryRepository::get(&conn, concession.cemetery_id).unwrap();
    let plot = PlotRepository::get(&conn, 1).ok();
    let burials = BurialRepository::list_by_concession(&conn, 1).unwrap_or_default();

    let output_dir = get_unique_test_dir();
    let result = PdfService::generate_concession_pdf(
        &concession,
        &cemetery,
        plot.as_ref(),
        None,
        &burials,
        &output_dir,
    );

    assert!(result.is_ok(), "PDF generation failed: {:?}", result);

    let pdf_path = result.unwrap();
    let verification = verify_pdf_file(&pdf_path);
    assert!(
        verification.is_ok(),
        "PDF validation failed: {:?}",
        verification.err()
    );

    // Cleanup
    let _ = fs::remove_file(&pdf_path);
    let _ = fs::remove_dir(output_dir);
}

#[test]
fn test_integration_pdf_with_burials() {
    let conn = setup_test_db();

    // Setup: create cemetery, plot, concession, and burial
    conn.execute(
        "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
        rusqlite::params![
            "Test Cemetery",
            "2026-06-16 10:00:00",
            "2026-06-16 10:00:00"
        ],
    )
    .unwrap();

    conn.execute(
        "INSERT INTO plots (cemetery_id, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 10, "available", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO concessions (cemetery_id, plot_id, concession_type, start_date, duration_years, expires_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rusqlite::params![
            1,
            1,
            "PERPETUELLE",
            "2026-06-16",
            Option::<i32>::None,
            Option::<String>::None,
            "PERPETUELLE",
            "2026-06-16T00:00:00Z",
            "2026-06-16T00:00:00Z"
        ],
    ).unwrap();

    conn.execute(
        "INSERT INTO individuals (name, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
        rusqlite::params![
            "John Doe",
            "beneficiary",
            "2026-06-16 10:00:00",
            "2026-06-16 10:00:00"
        ],
    )
    .unwrap();

    conn.execute(
        "INSERT INTO burials (concession_id, individual_id, buried_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 1, "2026-06-10", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    // Fetch data and generate PDF
    let concession = ConcessionRepository::get(&conn, 1).unwrap();
    let cemetery = CemeteryRepository::get(&conn, concession.cemetery_id).unwrap();
    let plot = PlotRepository::get(&conn, 1).ok();
    let burials = BurialRepository::list_by_concession(&conn, 1).unwrap_or_default();

    let output_dir = get_unique_test_dir();
    let result = PdfService::generate_concession_pdf(
        &concession,
        &cemetery,
        plot.as_ref(),
        None,
        &burials,
        &output_dir,
    );

    assert!(result.is_ok(), "PDF generation failed: {:?}", result);

    let pdf_path = result.unwrap();
    let verification = verify_pdf_file(&pdf_path);
    assert!(
        verification.is_ok(),
        "PDF validation failed: {:?}",
        verification.err()
    );

    assert_eq!(burials.len(), 1, "Should have one burial");

    // Cleanup
    let _ = fs::remove_file(&pdf_path);
    let _ = fs::remove_dir(output_dir);
}

#[test]
fn test_integration_pdf_with_multiple_burials() {
    let conn = setup_test_db();

    // Setup
    conn.execute(
        "INSERT INTO cemeteries (name, created_at, updated_at) VALUES (?, ?, ?)",
        rusqlite::params![
            "Test Cemetery",
            "2026-06-16 10:00:00",
            "2026-06-16 10:00:00"
        ],
    )
    .unwrap();

    conn.execute(
        "INSERT INTO plots (cemetery_id, capacity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        rusqlite::params![1, 10, "available", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
    ).unwrap();

    conn.execute(
        "INSERT INTO concessions (cemetery_id, plot_id, concession_type, start_date, duration_years, expires_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rusqlite::params![
            1,
            1,
            "PERPETUELLE",
            "2026-06-16",
            Option::<i32>::None,
            Option::<String>::None,
            "PERPETUELLE",
            "2026-06-16T00:00:00Z",
            "2026-06-16T00:00:00Z"
        ],
    ).unwrap();

    // Add multiple individuals
    for i in 1..=3 {
        conn.execute(
            "INSERT INTO individuals (name, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
            rusqlite::params![
                format!("Deceased {}", i),
                "deceased",
                "2026-06-16 10:00:00",
                "2026-06-16 10:00:00"
            ],
        )
        .unwrap();
    }

    // Add multiple burials
    for i in 1..=3 {
        conn.execute(
            "INSERT INTO burials (concession_id, individual_id, buried_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            rusqlite::params![1, i, "2026-06-10", "2026-06-16 10:00:00", "2026-06-16 10:00:00"],
        ).unwrap();
    }

    // Fetch data and generate PDF
    let concession = ConcessionRepository::get(&conn, 1).unwrap();
    let cemetery = CemeteryRepository::get(&conn, concession.cemetery_id).unwrap();
    let plot = PlotRepository::get(&conn, 1).ok();
    let burials = BurialRepository::list_by_concession(&conn, 1).unwrap_or_default();

    let output_dir = get_unique_test_dir();
    let result = PdfService::generate_concession_pdf(
        &concession,
        &cemetery,
        plot.as_ref(),
        None,
        &burials,
        &output_dir,
    );

    assert!(result.is_ok(), "PDF generation failed: {:?}", result);

    let pdf_path = result.unwrap();
    let verification = verify_pdf_file(&pdf_path);
    assert!(
        verification.is_ok(),
        "PDF validation failed: {:?}",
        verification.err()
    );

    assert_eq!(burials.len(), 3, "Should have three burials");

    // Cleanup
    let _ = fs::remove_file(&pdf_path);
    let _ = fs::remove_dir(output_dir);
}
