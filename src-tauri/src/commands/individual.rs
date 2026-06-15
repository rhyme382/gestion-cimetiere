use tauri::State;
use crate::{db::DbConnection, dto::*};

#[tauri::command]
pub fn list_individuals(_state: State<DbConnection>) -> Result<Vec<IndividualDTO>, String> {
    Ok(vec![])
}

#[tauri::command]
pub fn get_individual(_state: State<DbConnection>, _id: i64) -> Result<IndividualDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn create_individual(_state: State<DbConnection>, _req: CreateIndividualRequest) -> Result<IndividualDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn update_individual(_state: State<DbConnection>, _id: i64, _req: UpdateIndividualRequest) -> Result<IndividualDTO, String> {
    Err("Not implemented".to_string())
}

#[tauri::command]
pub fn search_individuals(_state: State<DbConnection>, _query: String) -> Result<Vec<IndividualDTO>, String> {
    Ok(vec![])
}
