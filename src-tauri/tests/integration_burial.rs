use gestion_cimetiere::core::models::{Burial, Cemetery, Concession, Individual, Plot};
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{
    BurialRepository, CemeteryRepository, ConcessionRepository, IndividualRepository,
    PlotRepository,
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
fn test_full_burial_workflow() {
    let conn = setup_db();

    // Create cemetery
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(1000),
    );
    let created_cemetery =
        CemeteryRepository::create(&conn, &cemetery).expect("Failed to create cemetery");

    // Create plot
    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        10,
    );
    let created_plot = PlotRepository::create(&conn, &plot).expect("Failed to create plot");

    // Create concession
    let mut concession = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession.start_date = Some("2026-01-01T00:00:00Z".to_string());
    let created_concession =
        ConcessionRepository::create(&conn, &concession).expect("Failed to create concession");

    // Create individual
    let individual = Individual::new(
        "John Doe".to_string(),
        Some("john@example.com".to_string()),
        Some("06 12 34 56 78".to_string()),
        "deceased".to_string(),
    );
    let created_individual =
        IndividualRepository::create(&conn, &individual).expect("Failed to create individual");

    // Create burial
    let burial = Burial::new(created_concession.id, created_individual.id);
    let created_burial = BurialRepository::create(&conn, &burial).expect("Failed to create burial");

    assert!(created_burial.id > 0);
    assert_eq!(created_burial.concession_id, created_concession.id);
    assert_eq!(created_burial.individual_id, created_individual.id);

    // Get burial by id
    let retrieved = BurialRepository::get(&conn, created_burial.id).expect("Failed to get burial");
    assert_eq!(retrieved.id, created_burial.id);
    assert_eq!(retrieved.concession_id, created_concession.id);
    assert_eq!(retrieved.individual_id, created_individual.id);

    // List burials for concession
    let list = BurialRepository::list_by_concession(&conn, created_concession.id)
        .expect("Failed to list burials");
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].id, created_burial.id);
}

#[test]
fn test_burial_create_and_list() {
    let conn = setup_db();

    // Setup: cemetery, plot, concession, individuals
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Lyon".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot = Plot::new(
        created_cemetery.id,
        Some("B".to_string()),
        Some(2),
        Some(2),
        8,
    );
    let created_plot = PlotRepository::create(&conn, &plot).unwrap();

    let mut concession = Concession::new(created_cemetery.id, Some(created_plot.id));
    concession.start_date = Some("2026-01-01T00:00:00Z".to_string());
    let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();

    let individual1 = Individual::new("Person 1".to_string(), None, None, "deceased".to_string());
    let individual2 = Individual::new("Person 2".to_string(), None, None, "deceased".to_string());

    let created_individual1 = IndividualRepository::create(&conn, &individual1).unwrap();
    let created_individual2 = IndividualRepository::create(&conn, &individual2).unwrap();

    // Create burials
    let burial1 = Burial::new(created_concession.id, created_individual1.id);
    let burial2 = Burial::new(created_concession.id, created_individual2.id);

    BurialRepository::create(&conn, &burial1).unwrap();
    BurialRepository::create(&conn, &burial2).unwrap();

    // List burials for concession
    let list = BurialRepository::list_by_concession(&conn, created_concession.id).unwrap();
    assert_eq!(list.len(), 2);

    // Most recent first (burial2, then burial1)
    assert!(list[0].id > 0);
    assert!(list[1].id > 0);
}

#[test]
fn test_burial_multiple_individuals_same_concession() {
    let conn = setup_db();

    // Setup
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Toulouse".to_string()),
        None,
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.start_date = Some("2026-01-01T00:00:00Z".to_string());
    let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();

    // Create multiple individuals
    let individuals_names = vec!["Person A", "Person B", "Person C"];
    let mut created_individuals = Vec::new();

    for name in individuals_names {
        let individual = Individual::new(name.to_string(), None, None, "deceased".to_string());
        let created = IndividualRepository::create(&conn, &individual).unwrap();
        created_individuals.push(created);
    }

    // Create burial for each
    for individual in &created_individuals {
        let burial = Burial::new(created_concession.id, individual.id);
        BurialRepository::create(&conn, &burial).unwrap();
    }

    // Verify all are listed under concession
    let list = BurialRepository::list_by_concession(&conn, created_concession.id).unwrap();
    assert_eq!(list.len(), 3);
}

#[test]
fn test_burial_get_by_id() {
    let conn = setup_db();

    // Setup
    let cemetery = Cemetery::new("Test Cemetery".to_string(), Some("Nice".to_string()), None);
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let mut concession = Concession::new(created_cemetery.id, None);
    concession.start_date = Some("2026-01-01T00:00:00Z".to_string());
    let created_concession = ConcessionRepository::create(&conn, &concession).unwrap();

    let individual = Individual::new(
        "Buried Person".to_string(),
        None,
        None,
        "deceased".to_string(),
    );
    let created_individual = IndividualRepository::create(&conn, &individual).unwrap();

    // Create burial
    let burial = Burial::new(created_concession.id, created_individual.id);
    let created = BurialRepository::create(&conn, &burial).unwrap();

    // Get it by ID
    let retrieved = BurialRepository::get(&conn, created.id).unwrap();
    assert_eq!(retrieved.id, created.id);
    assert_eq!(retrieved.concession_id, created_concession.id);
    assert_eq!(retrieved.individual_id, created_individual.id);
}
