use tauri::State;
use crate::{db::DbConnection, dto::*};

#[tauri::command]
pub fn list_plots(_state: State<DbConnection>, _cemetery_id: i64) -> Result<Vec<PlotDTO>, String> {
    Ok(vec![])
}

#[tauri::command]
pub fn get_plot(_state: State<DbConnection>, _id: i64) -> Result<PlotDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn create_plot(_state: State<DbConnection>, _req: CreatePlotRequest) -> Result<PlotDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn update_plot(_state: State<DbConnection>, _id: i64, _req: UpdatePlotRequest) -> Result<PlotDTO, String> {
    Err("Not implemented".to_string())
}
