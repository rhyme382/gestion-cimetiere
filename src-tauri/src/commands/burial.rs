use tauri::State;
use crate::{db::{DbConnection, repositories::BurialRepository}, core::models::Burial, dto::*};

#[tauri::command]
pub fn create_burial(state: State<DbConnection>, req: CreateBurialRequest) -> Result<BurialDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let mut burial = Burial::new(req.concession_id, req.individual_id);
    burial.buried_at = req.buried_at;
    BurialRepository::create(&conn, &burial).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_burial(state: State<DbConnection>, id: i64) -> Result<BurialDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    BurialRepository::get(&conn, id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_burials_by_concession(state: State<DbConnection>, concession_id: i64) -> Result<Vec<BurialDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    BurialRepository::list_by_concession(&conn, concession_id).map_err(|e| e.to_string())
}
