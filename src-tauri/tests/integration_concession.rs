use gestion_cimetiere::core::models::{Cemetery, Concession, Plot};
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{
    CemeteryRepository, ConcessionRepository, PlotRepository,
};
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
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
    let concession = Concession::new(created_cemetery.id, Some(created_plot.id));
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

    let concession1 = Concession::new(created_cemetery.id, None);
    let concession2 = Concession::new(created_cemetery.id, None);

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

    let concession1 = Concession::new(created_cemetery1.id, None);
    let concession2 = Concession::new(created_cemetery2.id, None);
    let concession3 = Concession::new(created_cemetery1.id, None);

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

    let concession = Concession::new(created_cemetery.id, Some(created_plot.id));
    let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();

    assert_eq!(created_concession.plot_id, Some(created_plot.id));

    // Verify it's in the list
    let list = ConcessionRepository::list(&conn, Some(created_cemetery.id)).unwrap();
    assert_eq!(list[0].plot_id, Some(created_plot.id));
}
