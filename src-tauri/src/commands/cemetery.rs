use crate::{
    core::models::Cemetery,
    db::repositories::CemeteryRepository,
    db::DbConnection,
    dto::*,
    errors::{ApiErrorResponse, AppError},
};
use rusqlite::Connection;
use tauri::State;

fn map_app_error(e: AppError) -> ApiErrorResponse {
    match e {
        AppError::NotFound(msg) => ApiErrorResponse {
            error_type: "NOT_FOUND".to_string(),
            message: msg,
        },
        AppError::InvalidInput(msg) => ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: msg,
        },
        AppError::Duplicate(msg) => ApiErrorResponse {
            error_type: "DUPLICATE".to_string(),
            message: msg,
        },
        AppError::Database(err) => ApiErrorResponse {
            error_type: "DATABASE_ERROR".to_string(),
            message: format!("Erreur base de données: {}", err),
        },
        AppError::Internal(msg) => ApiErrorResponse {
            error_type: "INTERNAL_ERROR".to_string(),
            message: msg,
        },
    }
}

pub fn internal_list_cemeteries(conn: &Connection) -> Result<Vec<CemeteryDTO>, AppError> {
    CemeteryRepository::list(conn)
}

pub fn internal_get_cemetery(conn: &Connection, id: i64) -> Result<CemeteryDTO, AppError> {
    CemeteryRepository::get(conn, id)
}

pub fn internal_create_cemetery(
    conn: &Connection,
    req: CreateCemeteryRequest,
) -> Result<CemeteryDTO, AppError> {
    conn.execute("BEGIN TRANSACTION", [])
        .map_err(AppError::Database)?;

    let mut cemetery = Cemetery::new(req.name, req.commune, req.capacity);
    cemetery.municipality_id = req.municipality_id;
    cemetery.address = req.address;

    match CemeteryRepository::create(conn, &cemetery) {
        Ok(result) => {
            conn.execute("COMMIT", []).map_err(AppError::Database)?;
            Ok(result)
        }
        Err(e) => {
            let _ = conn.execute("ROLLBACK", []);
            Err(e)
        }
    }
}

pub fn internal_update_cemetery(
    conn: &Connection,
    id: i64,
    req: UpdateCemeteryRequest,
) -> Result<CemeteryDTO, AppError> {
    conn.execute("BEGIN TRANSACTION", [])
        .map_err(AppError::Database)?;

    match (|| {
        let existing = CemeteryRepository::get(conn, id)?;
        let mut cemetery = Cemetery::new(
            req.name.unwrap_or(existing.name),
            req.commune.or(existing.commune),
            req.capacity.or(existing.capacity),
        );
        cemetery.id = id;
        cemetery.created_at = existing.created_at;
        cemetery.municipality_id = req.municipality_id.or(existing.municipality_id);
        cemetery.address = req.address.or(existing.address);
        cemetery.is_active = req.is_active.unwrap_or(existing.is_active);

        CemeteryRepository::update(conn, id, &cemetery)
    })() {
        Ok(result) => {
            conn.execute("COMMIT", []).map_err(AppError::Database)?;
            Ok(result)
        }
        Err(e) => {
            let _ = conn.execute("ROLLBACK", []);
            Err(e)
        }
    }
}

pub fn internal_delete_cemetery(conn: &Connection, id: i64) -> Result<bool, AppError> {
    conn.execute("BEGIN TRANSACTION", [])
        .map_err(AppError::Database)?;

    match CemeteryRepository::delete(conn, id) {
        Ok(result) => {
            conn.execute("COMMIT", []).map_err(AppError::Database)?;
            Ok(result)
        }
        Err(e) => {
            let _ = conn.execute("ROLLBACK", []);
            Err(e)
        }
    }
}

#[tauri::command]
pub fn list_cemeteries(state: State<DbConnection>) -> Result<Vec<CemeteryDTO>, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_list_cemeteries(&conn).map_err(map_app_error)
}

#[tauri::command]
pub fn get_cemetery(state: State<DbConnection>, id: i64) -> Result<CemeteryDTO, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_get_cemetery(&conn, id).map_err(map_app_error)
}

#[tauri::command]
pub fn create_cemetery(
    state: State<DbConnection>,
    req: CreateCemeteryRequest,
) -> Result<CemeteryDTO, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_create_cemetery(&conn, req).map_err(map_app_error)
}

#[tauri::command]
pub fn update_cemetery(
    state: State<DbConnection>,
    id: i64,
    req: UpdateCemeteryRequest,
) -> Result<CemeteryDTO, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_update_cemetery(&conn, id, req).map_err(map_app_error)
}

#[tauri::command]
pub fn delete_cemetery(state: State<DbConnection>, id: i64) -> Result<bool, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_delete_cemetery(&conn, id).map_err(map_app_error)
}
