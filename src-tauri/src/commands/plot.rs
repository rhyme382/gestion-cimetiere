use crate::{core::models::Plot, db::repositories::PlotRepository, db::DbConnection, dto::*};
use tauri::State;

#[tauri::command]
pub fn list_plots(state: State<DbConnection>, cemetery_id: i64) -> Result<Vec<PlotDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    PlotRepository::list(&conn, cemetery_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_plot(state: State<DbConnection>, id: i64) -> Result<PlotDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    PlotRepository::get(&conn, id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_plot(state: State<DbConnection>, req: CreatePlotRequest) -> Result<PlotDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let plot = Plot::new(
        req.cemetery_id,
        req.section,
        req.row,
        req.number,
        req.capacity,
    );
    PlotRepository::create(&conn, &plot).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_plot(
    state: State<DbConnection>,
    id: i64,
    req: UpdatePlotRequest,
) -> Result<PlotDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let existing = PlotRepository::get(&conn, id).map_err(|e| e.to_string())?;

    let mut plot = Plot::new(
        existing.cemetery_id,
        req.section.or(existing.section),
        req.row.or(existing.row),
        req.number.or(existing.number),
        req.capacity.unwrap_or(existing.capacity),
    );
    plot.id = id;
    plot.status = req.status.unwrap_or(existing.status);
    plot.created_at = existing.created_at;

    PlotRepository::update(&conn, id, &plot).map_err(|e| e.to_string())
}
