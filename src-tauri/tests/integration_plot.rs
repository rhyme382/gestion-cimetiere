use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::db::repositories::{CemeteryRepository, PlotRepository};
use gestion_cimetiere::core::models::{Cemetery, Plot};
use rusqlite::Connection;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

#[test]
fn test_full_plot_workflow() {
    let conn = setup_db();

    // Create a cemetery first
    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Paris".to_string()),
        Some(1000),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery)
        .expect("Failed to create cemetery");

    // Create a plot
    let plot = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        10,
    );

    let created_plot = PlotRepository::create(&conn, &plot).expect("Failed to create plot");
    assert!(created_plot.id > 0);
    assert_eq!(created_plot.cemetery_id, created_cemetery.id);
    assert_eq!(created_plot.section, Some("A".to_string()));
    assert_eq!(created_plot.row, Some(1));
    assert_eq!(created_plot.number, Some(1));
    assert_eq!(created_plot.capacity, 10);
    assert_eq!(created_plot.status, "available");

    // List plots for the cemetery
    let list = PlotRepository::list(&conn, created_cemetery.id).expect("Failed to list plots");
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].id, created_plot.id);

    // Get plot by id
    let retrieved = PlotRepository::get(&conn, created_plot.id).expect("Failed to get plot");
    assert_eq!(retrieved.id, created_plot.id);
    assert_eq!(retrieved.cemetery_id, created_cemetery.id);
}

#[test]
fn test_plot_create_and_list() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Lyon".to_string()),
        Some(500),
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot1 = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(1),
        5,
    );
    let plot2 = Plot::new(
        created_cemetery.id,
        Some("A".to_string()),
        Some(1),
        Some(2),
        5,
    );
    let plot3 = Plot::new(
        created_cemetery.id,
        Some("B".to_string()),
        Some(1),
        Some(1),
        8,
    );

    PlotRepository::create(&conn, &plot1).unwrap();
    PlotRepository::create(&conn, &plot2).unwrap();
    PlotRepository::create(&conn, &plot3).unwrap();

    let list = PlotRepository::list(&conn, created_cemetery.id).unwrap();
    assert_eq!(list.len(), 3);
    // Ordered by section, row, number
    assert_eq!(list[0].section, Some("A".to_string()));
    assert_eq!(list[0].number, Some(1));
    assert_eq!(list[1].number, Some(2));
    assert_eq!(list[2].section, Some("B".to_string()));
}

#[test]
fn test_plot_update() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Test Cemetery".to_string(),
        Some("Marseille".to_string()),
        None,
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let plot = Plot::new(
        created_cemetery.id,
        Some("C".to_string()),
        Some(5),
        Some(10),
        12,
    );

    let created = PlotRepository::create(&conn, &plot).unwrap();
    let id = created.id;

    let mut updated_plot = Plot::new(
        created_cemetery.id,
        Some("D".to_string()),
        Some(6),
        Some(11),
        15,
    );
    updated_plot.id = id;
    updated_plot.status = "occupied".to_string();

    let updated = PlotRepository::update(&conn, id, &updated_plot).unwrap();
    assert_eq!(updated.id, id);
    assert_eq!(updated.section, Some("D".to_string()));
    assert_eq!(updated.row, Some(6));
    assert_eq!(updated.number, Some(11));
    assert_eq!(updated.capacity, 15);
    assert_eq!(updated.status, "occupied");

    // Verify persistence
    let retrieved = PlotRepository::get(&conn, id).unwrap();
    assert_eq!(retrieved.section, Some("D".to_string()));
    assert_eq!(retrieved.status, "occupied");
}


#[test]
fn test_plot_empty_list_for_cemetery() {
    let conn = setup_db();

    let cemetery = Cemetery::new(
        "Empty Cemetery".to_string(),
        Some("Strasbourg".to_string()),
        None,
    );
    let created_cemetery = CemeteryRepository::create(&conn, &cemetery).unwrap();

    let list = PlotRepository::list(&conn, created_cemetery.id).unwrap();
    assert_eq!(list.len(), 0);
}
