// Tauri main entry point
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use gestion_cimetiere::{commands, db};
use std::fs;
use std::path::PathBuf;
use tauri::Manager;

fn main() {
    #[cfg(debug_assertions)]
    {
        let _ = gestion_cimetiere::export_bindings();
    }

    tauri::Builder::default()
        .setup(|app| {
            let db_path = if cfg!(debug_assertions) {
                PathBuf::from(":memory:")
            } else {
                let app_data_dir = app.path().app_data_dir().map_err(|error| {
                    std::io::Error::other(format!(
                        "Failed to resolve application data directory: {error}"
                    ))
                })?;

                fs::create_dir_all(&app_data_dir).map_err(|error| {
                    std::io::Error::new(
                        error.kind(),
                        format!(
                            "Failed to create application data directory '{}': {error}",
                            app_data_dir.display()
                        ),
                    )
                })?;

                app_data_dir.join("gestion_cimetiere.db")
            };

            let db_path_string = db_path.to_string_lossy().into_owned();

            let db_conn = db::init_db(&db_path_string).map_err(|error| {
                std::io::Error::other(format!(
                    "Failed to initialize database '{}': {error}",
                    db_path.display()
                ))
            })?;

            {
                let conn = db_conn
                    .lock()
                    .map_err(|_| std::io::Error::other("Database mutex is poisoned"))?;

                db::run_migrations(&conn).map_err(|error| {
                    std::io::Error::other(format!(
                        "Failed to run migrations on database '{}': {error}",
                        db_path.display()
                    ))
                })?;
            }

            app.manage(db_conn);
            app.manage(db_path_string);

            Ok(())
        })
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
            commands::get_diagnostic,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}
