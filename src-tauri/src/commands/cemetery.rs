use tauri::State;
use crate::{db::DbConnection, dto::*};

#[tauri::command]
pub fn list_cemeteries(_state: State<DbConnection>) -> Result<Vec<CemeteryDTO>, String> {
    // Stub implementation
    Ok(vec![])
}

#[tauri::command]
pub fn get_cemetery(_state: State<DbConnection>, _id: i64) -> Result<CemeteryDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn create_cemetery(_state: State<DbConnection>, _req: CreateCemeteryRequest) -> Result<CemeteryDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn update_cemetery(_state: State<DbConnection>, _id: i64, _req: UpdateCemeteryRequest) -> Result<CemeteryDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn delete_cemetery(_state: State<DbConnection>, _id: i64) -> Result<bool, String> {
    Err("Not implemented".to_string())
}
