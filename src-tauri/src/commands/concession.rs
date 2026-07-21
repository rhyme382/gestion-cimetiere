use crate::{
    core::models::Concession, db::repositories::ConcessionRepository, db::DbConnection, dto::*,
};
use tauri::State;

#[tauri::command]
pub fn list_concessions(
    state: State<DbConnection>,
    cemetery_id: Option<i64>,
) -> Result<Vec<ConcessionDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    ConcessionRepository::list(&conn, cemetery_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_concession(state: State<DbConnection>, id: i64) -> Result<ConcessionDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    ConcessionRepository::get(&conn, id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_concession(
    state: State<DbConnection>,
    req: CreateConcessionRequest,
) -> Result<ConcessionDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let mut concession = Concession::new(req.cemetery_id, req.plot_id);
    concession.concession_number = req.concession_number;
    concession.concession_type = req.concession_type;
    concession.duration_years = req.duration_years;
    concession.start_date = req.start_date;
    concession.holder_first_name = req.holder_first_name;
    concession.holder_last_name = req.holder_last_name;
    concession.holder_address = req.holder_address;
    concession.holder_postal_code = req.holder_postal_code;
    concession.holder_commune = req.holder_commune;
    concession.observations = req.observations;
    concession.acquired_at = req.acquired_at;
    ConcessionRepository::create(&conn, &concession).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn update_concession(
    state: State<DbConnection>,
    id: i64,
    req: UpdateConcessionRequest,
) -> Result<ConcessionDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    let existing = ConcessionRepository::get(&conn, id).map_err(|e| e.to_string())?;

    let mut concession = Concession::new(existing.cemetery_id, req.plot_id.or(existing.plot_id));
    concession.id = id;
    concession.concession_number = req.concession_number.or(existing.concession_number);
    concession.concession_type = req.concession_type.unwrap_or(existing.concession_type);
    concession.duration_years = req.duration_years.unwrap_or(existing.duration_years);
    concession.start_date = req.start_date.unwrap_or(existing.start_date);
    concession.holder_first_name = req.holder_first_name.or(existing.holder_first_name);
    concession.holder_last_name = req.holder_last_name.or(existing.holder_last_name);
    concession.holder_address = req.holder_address.or(existing.holder_address);
    concession.holder_postal_code = req.holder_postal_code.or(existing.holder_postal_code);
    concession.holder_commune = req.holder_commune.or(existing.holder_commune);
    concession.observations = req.observations.or(existing.observations);
    concession.acquired_at = req.acquired_at.or(existing.acquired_at);
    concession.renewed_at = req.renewed_at.or(existing.renewed_at);
    concession.created_at = existing.created_at;

    ConcessionRepository::update(&conn, id, &concession).map_err(|e| e.to_string())
}
