// Tauri main entry point
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use gestion_cimetiere::{commands, db};

fn main() {
    #[cfg(debug_assertions)]
    {
        let _ = gestion_cimetiere::export_bindings();
    }

    let db_path = if cfg!(debug_assertions) {
        ":memory:"
    } else {
        "gestion_cimetiere.db"
    };

    let db_conn = db::init_db(db_path).expect("Failed to initialize database");

    {
        let conn = db_conn.lock().unwrap();
        db::run_migrations(&conn).expect("Failed to run migrations");
    }

    tauri::Builder::default()
        .manage(db_conn)
        .manage(db_path.to_string())
        .invoke_handler(tauri::generate_handler![
            commands::list_cemeteries,
            commands::get_cemetery,
            commands::create_cemetery,
            commands::update_cemetery,
            commands::delete_cemetery,
            commands::list_plots,
            commands::get_plot,
            commands::create_plot,
            commands::update_plot,
            commands::list_concessions,
            commands::get_concession,
            commands::create_concession,
            commands::update_concession,
            commands::list_individuals,
            commands::get_individual,
            commands::create_individual,
            commands::update_individual,
            commands::search_individuals,
            commands::create_burial,
            commands::get_burial,
            commands::list_burials_by_concession,
            commands::list_alerts,
            commands::get_alert_summary,
            commands::refresh_alerts,
            commands::acknowledge_alert,
            commands::generate_concession_pdf,
            commands::create_backup,
            commands::list_backups,
            commands::restore_backup,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
