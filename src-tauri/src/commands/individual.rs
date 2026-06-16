use crate::{
    core::models::Individual,
    db::{repositories::IndividualRepository, DbConnection},
    dto::*,
};
use tauri::State;

#[tauri::command]
pub fn list_individuals(state: State<DbConnection>) -> Result<Vec<IndividualDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    IndividualRepository::list(&conn).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_individual(state: State<DbConnection>, id: i64) -> Result<IndividualDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    IndividualRepository::get(&conn, id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_individual(
    state: State<DbConnection>,
    req: CreateIndividualRequest,
) -> Result<IndividualDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let individual = Individual::new(req.name, req.email, req.phone, req.role);
    IndividualRepository::create(&conn, &individual).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_individual(
    state: State<DbConnection>,
    id: i64,
    req: UpdateIndividualRequest,
) -> Result<IndividualDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let existing = IndividualRepository::get(&conn, id).map_err(|e| e.to_string())?;
    let individual = Individual::new(
        req.name.unwrap_or(existing.name),
        req.email.or(existing.email),
        req.phone.or(existing.phone),
        req.role.unwrap_or(existing.role),
    );
    IndividualRepository::update(&conn, id, &individual).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn search_individuals(
    state: State<DbConnection>,
    query: String,
) -> Result<Vec<IndividualDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    IndividualRepository::search(&conn, &query).map_err(|e| e.to_string())
}
