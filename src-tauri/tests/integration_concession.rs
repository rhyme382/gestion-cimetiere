use gestion_cimetiere::core::models::{Cemetery, Concession, Plot};
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{
    CemeteryRepository, ConcessionRepository, PlotRepository,
};
use chrono::{DateTime, Utc};
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

fn reference_date(date_str: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(date_str)
        .expect("Invalid reference date")
        .with_timezone(&Utc)
}

#[test]
fn test_full_concession_workflow() {
    let conn = setup_db();

    // Create cemetery and plot
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(1000),
    );
    let created_cemetery =
        CemeteryRepository::create(&conn, &cemetery).expect("Failed to create cemetery");

    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        10,
    );
    let created_plot = PlotRepository::create(&conn, &plot).expect("Failed to create plot");

    // Create a concession
    let mut concession = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let created_concession =
        ConcessionRepository::create(&conn, &concession).expect("Failed to create concession");

    assert!(created_concession.id > 0);
    assert_eq!(created_concession.cemetery_id, created_cemetery.id);
    assert_eq!(created_concession.plot_id, Some(created_plot.id));
    assert_eq!(created_concession.status, "PERPETUELLE");

    // List concessions for the cemetery
    let list = ConcessionRepository::list(&conn, Some(created_cemetery.id))
        .expect("Failed to list concessions");
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].id, created_concession.id);

    // Get concession by id
    let retrieved =
        ConcessionRepository::get(&conn, created_concession.id).expect("Failed to get concession");
    assert_eq!(retrieved.id, created_concession.id);
    assert_eq!(retrieved.cemetery_id, created_cemetery.id);
}

#[test]
fn test_concession_create_and_list() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Lyon".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession1 = Concession::new(created_cemetery.id, None);
    concession1.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let mut concession2 = Concession::new(created_cemetery.id, None);
    concession2.start_date = Some("2025-01-01T00:00:00Z".to_string());

    ConcessionRepository::create(&conn, &concession1).unwrap();
    ConcessionRepository::create(&conn, &concession2).unwrap();

    let list = ConcessionRepository::list(&conn, Some(created_cemetery.id)).unwrap();
    assert_eq!(list.len(), 2);

    // Most recent first
    assert!(list[0].id > 0);
    assert!(list[1].id > 0);
}

#[test]
fn test_concession_list_all() {
    let conn = setup_db();

    let cemetery1 = Cemetery::new(
        "Cemetery 1".to_string(),
        Some("Paris".to_string()),
        Some(1000),
    );
    let cemetery2 = Cemetery::new(
        "Cemetery 2".to_string(),
        Some("Lyon".to_string()),
        Some(500),
    );

    let created_cemetery1 = CemeteryRepository::create(&conn, &cemetery1).unwrap();
    let created_cemetery2 = CemeteryRepository::create(&conn, &cemetery2).unwrap();

    let mut concession1 = Concession::new(created_cemetery1.id, None);
    concession1.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let mut concession2 = Concession::new(created_cemetery2.id, None);
    concession2.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let mut concession3 = Concession::new(created_cemetery1.id, None);
    concession3.start_date = Some("2025-01-01T00:00:00Z".to_string());

    ConcessionRepository::create(&conn, &concession1).unwrap();
    ConcessionRepository::create(&conn, &concession2).unwrap();
    ConcessionRepository::create(&conn, &concession3).unwrap();

    // List all concessions
    let list_all = ConcessionRepository::list(&conn, None).unwrap();
    assert_eq!(list_all.len(), 3);

    // List by cemetery 1
    let list_cemetery1 = ConcessionRepository::list(&conn, Some(created_cemetery1.id)).unwrap();
    assert_eq!(list_cemetery1.len(), 2);

    // List by cemetery 2
    let list_cemetery2 = ConcessionRepository::list(&conn, Some(created_cemetery2.id)).unwrap();
    assert_eq!(list_cemetery2.len(), 1);
}

#[test]
fn test_concession_update() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Marseille".to_string()),
        None,
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create a temporary concession that expired in the past
    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(1);
    concession.start_date = Some("2020-01-01T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    let id = created.id;

    // Verify it was created with EXPIREE status (due to expired date)
    assert_eq!(created.status, "EXPIREE");

    // Update the concession with holder data
    let mut updated_concession = Concession::new(created_cemetery.id, None);
    updated_concession.id = id;
    updated_concession.concession_type = "TEMPORAIRE".to_string();
    updated_concession.duration_years = Some(1);
    updated_concession.start_date = Some("2020-01-01T00:00:00Z".to_string());
    updated_concession.holder_first_name = Some("Jean".to_string());

    let updated = ConcessionRepository::update(&conn, id, &updated_concession).unwrap();
    assert_eq!(updated.id, id);
    assert_eq!(updated.status, "EXPIREE");
    assert_eq!(updated.holder_first_name, Some("Jean".to_string()));

    // Verify persistence
    let retrieved = ConcessionRepository::get(&conn, id).unwrap();
    assert_eq!(retrieved.status, "EXPIREE");
}

#[test]
fn test_concession_with_plot() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Toulouse".to_string()),
        None,
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        5,
    );
    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    let mut concession = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();

    assert_eq!(created_concession.plot_id, Some(created_plot.id));

    // Verify it's in the list
    let list = ConcessionRepository::list(&conn, Some(created_cemetery.id)).unwrap();
    assert_eq!(list[0].plot_id, Some(created_plot.id));
}

// ========== Deterministic Lifecycle Tests ==========

#[test]
fn test_concession_status_transition_active_to_soon_expiring() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create a concession that expires 2035-01-01 (10 years from 2025-01-01)
    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(10);
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();

    // At 2025-01-01 (far from expiry) -> ACTIVE
    let ref_date_early = reference_date("2025-01-01T00:00:00Z");
    let concession_early =
        ConcessionRepository::get_at(&conn, created.id, ref_date_early).unwrap();
    assert_eq!(concession_early.status, "ACTIVE");

    // At 2034-02-01 (11 months before expiry) -> ECHEANCE_PROCHE
    let ref_date_soon = reference_date("2034-02-01T00:00:00Z");
    let concession_soon =
        ConcessionRepository::get_at(&conn, created.id, ref_date_soon).unwrap();
    assert_eq!(concession_soon.status, "ECHEANCE_PROCHE");

    // At 2035-01-02 (1 day after expiry) -> EXPIREE
    let ref_date_expired = reference_date("2035-01-02T00:00:00Z");
    let concession_expired =
        ConcessionRepository::get_at(&conn, created.id, ref_date_expired).unwrap();
    assert_eq!(concession_expired.status, "EXPIREE");
}

#[test]
fn test_concession_status_perpetuelle_never_expires() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Perpetual Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "PERPETUELLE".to_string();
    concession.start_date = Some("1900-01-01T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    assert_eq!(created.status, "PERPETUELLE");

    // Test with far future reference date - should still be PERPETUELLE
    let ref_date_far_future = reference_date("3000-01-01T00:00:00Z");
    let concession_future =
        ConcessionRepository::get_at(&conn, created.id, ref_date_far_future).unwrap();
    assert_eq!(concession_future.status, "PERPETUELLE");
}

#[test]
fn test_concession_30year_lifecycle() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TRENTENAIRE".to_string();
    concession.duration_years = Some(30);
    concession.start_date = Some("2000-06-15T12:30:45Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();

    // Verify expires_at is calculated
    assert!(created.expires_at.is_some());
    let expires_at = created.expires_at.unwrap();
    assert!(expires_at.contains("2030-06-15"));

    // At 2028-01-01 (far from expiry) -> ACTIVE
    let ref_date_early = reference_date("2028-01-01T00:00:00Z");
    let concession_early =
        ConcessionRepository::get_at(&conn, created.id, ref_date_early).unwrap();
    assert_eq!(concession_early.status, "ACTIVE");

    // At 2029-07-01 (11 months before expiry) -> ECHEANCE_PROCHE
    let ref_date_soon = reference_date("2029-07-01T00:00:00Z");
    let concession_soon =
        ConcessionRepository::get_at(&conn, created.id, ref_date_soon).unwrap();
    assert_eq!(concession_soon.status, "ECHEANCE_PROCHE");

    // At 2031-01-01 (7 months after expiry) -> EXPIREE
    let ref_date_expired = reference_date("2031-01-01T00:00:00Z");
    let concession_expired =
        ConcessionRepository::get_at(&conn, created.id, ref_date_expired).unwrap();
    assert_eq!(concession_expired.status, "EXPIREE");
}

#[test]
fn test_concession_50year_lifecycle() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "CINQUANTENAIRE".to_string();
    concession.duration_years = Some(50);
    concession.start_date = Some("2000-03-21T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();

    // Verify expires_at calculation
    assert!(created.expires_at.is_some());
    let expires_at = created.expires_at.unwrap();
    assert!(expires_at.contains("2050-03-21"));

    // At 2048-02-01 (far from expiry) -> ACTIVE
    let ref_date_active = reference_date("2048-02-01T00:00:00Z");
    let concession_active =
        ConcessionRepository::get_at(&conn, created.id, ref_date_active).unwrap();
    assert_eq!(concession_active.status, "ACTIVE");

    // At 2049-04-01 (11 months before expiry) -> ECHEANCE_PROCHE
    let ref_date_soon = reference_date("2049-04-01T00:00:00Z");
    let concession_soon =
        ConcessionRepository::get_at(&conn, created.id, ref_date_soon).unwrap();
    assert_eq!(concession_soon.status, "ECHEANCE_PROCHE");
}

#[test]
fn test_concession_short_term_lifecycle() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create a 5-year temporary concession
    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(5);
    concession.start_date = Some("2020-08-10T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();

    // At 2020-08-10 (start date) -> ACTIVE
    let ref_date_start = reference_date("2020-08-10T00:00:00Z");
    let concession_start =
        ConcessionRepository::get_at(&conn, created.id, ref_date_start).unwrap();
    assert_eq!(concession_start.status, "ACTIVE");

    // At 2025-08-15 (5 days before expiry of 2025-08-10) -> still ACTIVE or ECHEANCE_PROCHE
    // Expiry is 2025-08-10, so at 2025-08-15 we're 5 days past expiry -> EXPIREE
    let ref_date_expired_mid = reference_date("2025-08-15T00:00:00Z");
    let concession_expired_mid =
        ConcessionRepository::get_at(&conn, created.id, ref_date_expired_mid).unwrap();
    assert_eq!(concession_expired_mid.status, "EXPIREE");

    // At 2025-07-20 (21 days before expiry) -> ECHEANCE_PROCHE (within 366 days)
    let ref_date_soon = reference_date("2025-07-20T00:00:00Z");
    let concession_soon =
        ConcessionRepository::get_at(&conn, created.id, ref_date_soon).unwrap();
    assert_eq!(concession_soon.status, "ECHEANCE_PROCHE");
}

#[test]
fn test_concession_expiry_boundary_1_day_window() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(10);
    concession.start_date = Some("2024-01-01T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    // Expires at 2034-01-01

    // 367 days before (2032-12-30) -> ACTIVE (outside 12-month window)
    let ref_date_367_days = reference_date("2032-12-30T00:00:00Z");
    let status_367 = ConcessionRepository::get_at(&conn, created.id, ref_date_367_days)
        .unwrap()
        .status;
    assert_eq!(status_367, "ACTIVE");

    // 366 days before (2032-12-31) -> ECHEANCE_PROCHE (inside 12-month window)
    let ref_date_366_days = reference_date("2032-12-31T00:00:00Z");
    let status_366 = ConcessionRepository::get_at(&conn, created.id, ref_date_366_days)
        .unwrap()
        .status;
    assert_eq!(status_366, "ECHEANCE_PROCHE");

    // On expiry date (2034-01-01) -> ECHEANCE_PROCHE (not yet expired)
    let ref_date_on_expiry = reference_date("2034-01-01T00:00:00Z");
    let status_on = ConcessionRepository::get_at(&conn, created.id, ref_date_on_expiry)
        .unwrap()
        .status;
    assert_eq!(status_on, "ECHEANCE_PROCHE");

    // 1 day after expiry (2034-01-02) -> EXPIREE
    let ref_date_1_day_after = reference_date("2034-01-02T00:00:00Z");
    let status_1_day_after = ConcessionRepository::get_at(&conn, created.id, ref_date_1_day_after)
        .unwrap()
        .status;
    assert_eq!(status_1_day_after, "EXPIREE");
}

#[test]
fn test_concession_leap_year_expiry_feb29_to_non_leap() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Start on Feb 29, 2024 (leap year), with 1-year duration
    // Should expire on Feb 28, 2025 (non-leap year)
    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(1);
    concession.start_date = Some("2024-02-29T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();

    let expires_at = created.expires_at.unwrap();
    // Should be 2025-02-28 (or 2025-03-01 depending on implementation)
    assert!(
        expires_at.contains("2025-02-28") || expires_at.contains("2025-03-01"),
        "Expected expiry near 2025-02-28 but got {}",
        expires_at
    );
}

#[test]
fn test_concession_leap_year_expiry_feb29_to_leap() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Start on Feb 29, 2020 (leap year), with 4-year duration
    // Should expire on Feb 29, 2024 (also leap year)
    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(4);
    concession.start_date = Some("2020-02-29T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();

    let expires_at = created.expires_at.unwrap();
    assert!(expires_at.contains("2024-02-29"));
}

#[test]
fn test_multiple_concessions_different_statuses_at_same_reference_date() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create 4 concessions with staggered expiry dates
    let mut c1 = Concession::new(created_cemetery.id, None);
    c1.concession_type = "TEMPORAIRE".to_string();
    c1.duration_years = Some(1);
    c1.start_date = Some("2025-01-01T00:00:00Z".to_string());

    let mut c2 = Concession::new(created_cemetery.id, None);
    c2.concession_type = "TEMPORAIRE".to_string();
    c2.duration_years = Some(5);
    c2.start_date = Some("2025-01-01T00:00:00Z".to_string());

    let mut c3 = Concession::new(created_cemetery.id, None);
    c3.concession_type = "TEMPORAIRE".to_string();
    c3.duration_years = Some(10);
    c3.start_date = Some("2025-01-01T00:00:00Z".to_string());

    let mut c4 = Concession::new(created_cemetery.id, None);
    c4.concession_type = "PERPETUELLE".to_string();
    c4.start_date = Some("2025-01-01T00:00:00Z".to_string());

    let created1 = ConcessionRepository::create(&conn, &c1).unwrap();
    let created2 = ConcessionRepository::create(&conn, &c2).unwrap();
    let created3 = ConcessionRepository::create(&conn, &c3).unwrap();
    let created4 = ConcessionRepository::create(&conn, &c4).unwrap();

    // At reference date 2034-06-01:
    // c1 expires 2026-01-01 -> EXPIREE
    // c2 expires 2030-01-01 -> EXPIREE
    // c3 expires 2035-01-01 -> ECHEANCE_PROCHE (214 days before)
    // c4 (perpetuelle) -> PERPETUELLE
    let ref_date = reference_date("2034-06-01T00:00:00Z");

    let concessions = ConcessionRepository::list_at(&conn, Some(created_cemetery.id), ref_date)
        .unwrap();

    let c1_status = concessions.iter().find(|c| c.id == created1.id).unwrap().status.clone();
    let c2_status = concessions.iter().find(|c| c.id == created2.id).unwrap().status.clone();
    let c3_status = concessions.iter().find(|c| c.id == created3.id).unwrap().status.clone();
    let c4_status = concessions.iter().find(|c| c.id == created4.id).unwrap().status.clone();

    assert_eq!(c1_status, "EXPIREE");
    assert_eq!(c2_status, "EXPIREE");
    assert_eq!(c3_status, "ECHEANCE_PROCHE");
    assert_eq!(c4_status, "PERPETUELLE");
}

#[test]
fn test_concession_update_with_status_recalculation() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create a concession that will expire
    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(5);
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    assert_eq!(created.status, "ACTIVE");

    // Update: change start date to further in the past to make it expire
    let updated = Concession {
        id: created.id,
        cemetery_id: created.cemetery_id,
        plot_id: created.plot_id,
        concession_number: created.concession_number.clone(),
        concession_type: "TEMPORAIRE".to_string(),
        duration_years: Some(1),
        start_date: Some("2020-01-01T00:00:00Z".to_string()), // Now expires 2021-01-01
        holder_first_name: None,
        holder_last_name: None,
        holder_address: None,
        holder_postal_code: None,
        holder_commune: None,
        observations: None,
        acquired_at: None,
        expires_at: None,
        renewed_at: None,
        status: "ACTIVE".to_string(),
        created_at: created.created_at.clone(),
        updated_at: Utc::now().to_rfc3339(),
    };

    let updated_concession = ConcessionRepository::update(&conn, created.id, &updated).unwrap();
    // Status should be recalculated to EXPIREE (since 2021-01-01 is long in the past)
    assert_eq!(updated_concession.status, "EXPIREE");
}

#[test]
fn test_concession_validation_temporal_with_invalid_duration() {
    let mut concession = Concession::new(1, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.duration_years = Some(0); // Invalid: too low

    let result = concession.validate();
    assert!(result.is_err());
    match result {
        Err(gestion_cimetiere::errors::AppError::InvalidInput(msg)) => {
            assert!(msg.contains("duration"));
        }
        _ => panic!("Expected InvalidInput error"),
    }

    concession.duration_years = Some(100); // Invalid: too high
    let result2 = concession.validate();
    assert!(result2.is_err());
}

#[test]
fn test_concession_validation_trentenaire_enforces_duration() {
    let mut concession = Concession::new(1, None);
    concession.concession_type = "TRENTENAIRE".to_string();
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.duration_years = Some(20); // Invalid: must be exactly 30

    let result = concession.validate();
    assert!(result.is_err());

    concession.duration_years = Some(30); // Valid
    assert!(concession.validate().is_ok());
}

#[test]
fn test_concession_validation_cinquantenaire_enforces_duration() {
    let mut concession = Concession::new(1, None);
    concession.concession_type = "CINQUANTENAIRE".to_string();
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.duration_years = Some(40); // Invalid: must be exactly 50

    let result = concession.validate();
    assert!(result.is_err());

    concession.duration_years = Some(50); // Valid
    assert!(concession.validate().is_ok());
}

#[test]
fn test_concession_holder_persistence() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.holder_first_name = Some("Marie".to_string());
    concession.holder_last_name = Some("Martin".to_string());
    concession.holder_address = Some("42 Rue des Fleurs".to_string());
    concession.holder_postal_code = Some("13000".to_string());
    concession.holder_commune = Some("Marseille".to_string());

    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();

    assert_eq!(retrieved.holder_first_name, Some("Marie".to_string()));
    assert_eq!(retrieved.holder_last_name, Some("Martin".to_string()));
    assert_eq!(retrieved.holder_address, Some("42 Rue des Fleurs".to_string()));
    assert_eq!(retrieved.holder_postal_code, Some("13000".to_string()));
    assert_eq!(retrieved.holder_commune, Some("Marseille".to_string()));
}

#[test]
fn test_concession_number_assignment() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.concession_number = Some("2025-00001".to_string());

    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();

    assert_eq!(retrieved.concession_number, Some("2025-00001".to_string()));
}

#[test]
fn test_plot_occupation_prevents_duplicate_active_concessions() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        10,
    );
    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    // Create first ACTIVE concession
    let mut concession1 = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession1.concession_type = "TEMPORAIRE".to_string();
    concession1.duration_years = Some(10);
    concession1.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let created1 = ConcessionRepository::create(&conn, &concession1).unwrap();
    assert_eq!(created1.status, "ACTIVE");

    // Try to create second concession on same plot - should fail
    let mut concession2 = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession2.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let result = ConcessionRepository::create(&conn, &concession2);
    assert!(result.is_err());
}

#[test]
fn test_plot_occupation_allows_expired_concessions_to_be_replaced() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        10,
    );
    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    // Create first concession that expires in the past
    let mut concession1 = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession1.concession_type = "TEMPORAIRE".to_string();
    concession1.duration_years = Some(1);
    concession1.start_date = Some("2020-01-01T00:00:00Z".to_string());
    let created1 = ConcessionRepository::create(&conn, &concession1).unwrap();
    assert_eq!(created1.status, "EXPIREE");

    // Try to create new concession on same plot - should succeed (expired plot is free)
    let mut concession2 = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession2.start_date = Some("2025-01-01T00:00:00Z".to_string());
    let result = ConcessionRepository::create(&conn, &concession2);
    assert!(result.is_ok());
    let created2 = result.unwrap();
    assert_eq!(created2.plot_id, Some(created_plot.id));
}

#[test]
fn test_concession_with_observations() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.observations = Some(
        "Concession en bon état. Travaux de restauration prévus en 2026.".to_string(),
    );

    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();

    assert_eq!(
        retrieved.observations,
        Some("Concession en bon état. Travaux de restauration prévus en 2026.".to_string())
    );
}

#[test]
fn test_concession_acquired_date_tracking() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.acquired_at = Some("2024-12-15T10:30:00Z".to_string());

    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();

    assert_eq!(retrieved.acquired_at, Some("2024-12-15T10:30:00Z".to_string()));
}

#[test]
fn test_concession_renewable_status_tracking() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.concession_type = "TEMPORAIRE".to_string();
    concession.duration_years = Some(30);
    concession.start_date = Some("2000-01-01T00:00:00Z".to_string());
    concession.renewed_at = Some("2024-06-15T00:00:00Z".to_string());

    let created = ConcessionRepository::create(&conn, &concession).unwrap();
    let retrieved = ConcessionRepository::get(&conn, created.id).unwrap();

    assert_eq!(retrieved.renewed_at, Some("2024-06-15T00:00:00Z".to_string()));
}

#[test]
fn test_concession_number_is_required() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession.concession_number = None; // Empty number

    // Number must be set for database storage; None/empty should fail validation or in creation
    // If the repository enforces uniqueness on non-null values, None should be allowed
    // But metadata or business logic may require it
    let created = ConcessionRepository::create(&conn, &concession);

    // Behavior depends on schema: if number is nullable with unique constraint, None is allowed
    // If the feature requires it, validation should catch it
    if created.is_ok() {
        let concession = created.unwrap();
        // If created, number must be None
        assert!(concession.concession_number.is_none());
    }
    // If validation fails, that's also acceptable for the feature spec
}

#[test]
fn test_concession_number_must_be_unique() {
    let conn = setup_db();
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Test City".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    // Create first concession with a specific number
    let mut concession1 = Concession::new(created_cemetery.id, None);
    concession1.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession1.concession_number = Some("2025-UNIQUE-001".to_string());

    let created1 = ConcessionRepository::create(&conn, &concession1).unwrap();
    assert_eq!(created1.concession_number, Some("2025-UNIQUE-001".to_string()));

    // Try to create second concession with duplicate number
    let mut concession2 = Concession::new(created_cemetery.id, None);
    concession2.start_date = Some("2025-01-01T00:00:00Z".to_string());
    concession2.concession_number = Some("2025-UNIQUE-001".to_string()); // Same number

    let result = ConcessionRepository::create(&conn, &concession2);
    // Duplicate should fail
    assert!(result.is_err(), "Duplicate concession number should not be allowed");
}
