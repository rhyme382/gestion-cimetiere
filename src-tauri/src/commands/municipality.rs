use crate::{
    core::models::Municipality,
    db::repositories::MunicipalityRepository,
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

pub fn internal_list_municipalities(conn: &Connection) -> Result<Vec<MunicipalityDTO>, AppError> {
    MunicipalityRepository::list(conn)
}

pub fn internal_get_municipality(conn: &Connection, id: i64) -> Result<MunicipalityDTO, AppError> {
    MunicipalityRepository::get(conn, id)
}

pub fn internal_create_municipality(
    conn: &Connection,
    req: CreateMunicipalityRequest,
) -> Result<MunicipalityDTO, AppError> {
    conn.execute("BEGIN TRANSACTION", [])
        .map_err(AppError::Database)?;

    let municipality = Municipality::new(req.name, req.insee_code, req.postal_code, req.email);
    match MunicipalityRepository::create(conn, &municipality) {
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

pub fn internal_update_municipality(
    conn: &Connection,
    id: i64,
    req: UpdateMunicipalityRequest,
) -> Result<MunicipalityDTO, AppError> {
    conn.execute("BEGIN TRANSACTION", [])
        .map_err(AppError::Database)?;

    match (|| {
        let existing = MunicipalityRepository::get(conn, id)?;
        let mut municipality = Municipality::new(
            req.name.unwrap_or(existing.name),
            req.insee_code.unwrap_or(existing.insee_code),
            req.postal_code.or(existing.postal_code),
            req.email.or(existing.email),
        );
        municipality.id = id;
        municipality.created_at = existing.created_at;
        municipality.department = req.department.or(existing.department);
        municipality.region = req.region.or(existing.region);
        municipality.notes = req.notes.or(existing.notes);

        MunicipalityRepository::update(conn, id, &municipality)
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

pub fn internal_delete_municipality(conn: &Connection, id: i64) -> Result<(), AppError> {
    conn.execute("BEGIN TRANSACTION", [])
        .map_err(AppError::Database)?;

    match MunicipalityRepository::delete(conn, id) {
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
pub fn list_municipalities(
    state: State<DbConnection>,
) -> Result<Vec<MunicipalityDTO>, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_list_municipalities(&conn).map_err(map_app_error)
}

#[tauri::command]
pub fn get_municipality(
    state: State<DbConnection>,
    id: i64,
) -> Result<MunicipalityDTO, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_get_municipality(&conn, id).map_err(map_app_error)
}

#[tauri::command]
pub fn create_municipality(
    state: State<DbConnection>,
    req: CreateMunicipalityRequest,
) -> Result<MunicipalityDTO, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_create_municipality(&conn, req).map_err(map_app_error)
}

#[tauri::command]
pub fn update_municipality(
    state: State<DbConnection>,
    id: i64,
    req: UpdateMunicipalityRequest,
) -> Result<MunicipalityDTO, ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_update_municipality(&conn, id, req).map_err(map_app_error)
}

#[tauri::command]
pub fn delete_municipality(state: State<DbConnection>, id: i64) -> Result<(), ApiErrorResponse> {
    let conn = state.lock().map_err(|e| ApiErrorResponse {
        error_type: "INTERNAL_ERROR".to_string(),
        message: format!("Failed to acquire database lock: {}", e),
    })?;
    internal_delete_municipality(&conn, id).map_err(map_app_error)
}
