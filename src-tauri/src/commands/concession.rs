use tauri::State;
use crate::{db::DbConnection, dto::*};

#[tauri::command]
pub fn list_concessions(_state: State<DbConnection>, _cemetery_id: Option<i64>) -> Result<Vec<ConcessionDTO>, String> {
    Ok(vec![])
}

#[tauri::command]
pub fn get_concession(_state: State<DbConnection>, _id: i64) -> Result<ConcessionDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn create_concession(_state: State<DbConnection>, _req: CreateConcessionRequest) -> Result<ConcessionDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn update_concession(_state: State<DbConnection>, _id: i64, _req: UpdateConcessionRequest) -> Result<ConcessionDTO, String> {
    Err("Not implemented".to_string())
}
