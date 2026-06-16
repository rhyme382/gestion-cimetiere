use crate::{
    core::models::Cemetery, db::repositories::CemeteryRepository, db::DbConnection, dto::*,
};
use tauri::State;

#[tauri::command]
pub fn list_cemeteries(state: State<DbConnection>) -> Result<Vec<CemeteryDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    CemeteryRepository::list(&conn).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_cemetery(state: State<DbConnection>, id: i64) -> Result<CemeteryDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    CemeteryRepository::get(&conn, id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_cemetery(
    state: State<DbConnection>,
    req: CreateCemeteryRequest,
) -> Result<CemeteryDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let cemetery = Cemetery::new(req.name, req.commune, req.capacity);
    CemeteryRepository::create(&conn, &cemetery).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_cemetery(
    state: State<DbConnection>,
    id: i64,
    req: UpdateCemeteryRequest,
) -> Result<CemeteryDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let existing = CemeteryRepository::get(&conn, id).map_err(|e| e.to_string())?;

    let mut cemetery = Cemetery::new(
        req.name.unwrap_or(existing.name),
        req.commune.or(existing.commune),
        req.capacity.or(existing.capacity),
    );
    cemetery.id = id;
    cemetery.created_at = existing.created_at;

    CemeteryRepository::update(&conn, id, &cemetery).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_cemetery(state: State<DbConnection>, id: i64) -> Result<bool, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    CemeteryRepository::delete(&conn, id).map_err(|e| e.to_string())
}
