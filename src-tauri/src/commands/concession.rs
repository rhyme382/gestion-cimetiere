use crate::{
    core::models::Concession,
    db::repositories::{CemeteryRepository, ConcessionRepository, PlotRepository},
    db::DbConnection,
    dto::*,
    errors::AppError,
};
use tauri::State;

#[tauri::command]
pub fn list_concessions(
    state: State<DbConnection>,
    cemetery_id: Option<i64>,
) -> Result<Vec<ConcessionDTO>, crate::errors::ApiErrorResponse> {
    let conn = state.lock().map_err(|e| {
        crate::errors::ApiErrorResponse {
            error_type: "INTERNAL_ERROR".to_string(),
            message: format!("Failed to acquire database lock: {}", e),
        }
    })?;
    ConcessionRepository::list(&conn, cemetery_id)
        .map_err(|e| map_app_error(e))
}

#[tauri::command]
pub fn get_concession(
    state: State<DbConnection>,
    id: i64,
) -> Result<ConcessionDTO, crate::errors::ApiErrorResponse> {
    let conn = state.lock().map_err(|e| {
        crate::errors::ApiErrorResponse {
            error_type: "INTERNAL_ERROR".to_string(),
            message: format!("Failed to acquire database lock: {}", e),
        }
    })?;
    ConcessionRepository::get(&conn, id).map_err(|e| map_app_error(e))
}

#[tauri::command]
pub fn create_concession(
    state: State<DbConnection>,
    req: CreateConcessionRequest,
) -> Result<ConcessionDTO, crate::errors::ApiErrorResponse> {
    let mut conn = state.lock().map_err(|e| {
        crate::errors::ApiErrorResponse {
            error_type: "INTERNAL_ERROR".to_string(),
            message: format!("Failed to acquire database lock: {}", e),
        }
    })?;

    validate_create_concession_request(&conn, &req)?;

    // Use transaction for atomic write
    let tx = conn.transaction().map_err(|e| {
        crate::errors::ApiErrorResponse {
            error_type: "DATABASE_ERROR".to_string(),
            message: format!("Failed to start transaction: {}", e),
        }
    })?;

    let mut concession = Concession::new(req.cemetery_id, Some(req.plot_id));
    concession.concession_number = Some(req.concession_number);
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

    ConcessionRepository::create_in_tx(&tx, &concession)
        .and_then(|result| {
            tx.commit()
                .map(|_| result)
                .map_err(|e| {
                    AppError::Database(e)
                })
        })
        .map_err(|e| map_app_error(e))
}

#[tauri::command]
pub fn update_concession(
    state: State<DbConnection>,
    id: i64,
    req: UpdateConcessionRequest,
) -> Result<ConcessionDTO, crate::errors::ApiErrorResponse> {
    let mut conn = state.lock().map_err(|e| {
        crate::errors::ApiErrorResponse {
            error_type: "INTERNAL_ERROR".to_string(),
            message: format!("Failed to acquire database lock: {}", e),
        }
    })?;

    validate_update_concession_request(&conn, &req)?;

    // Use transaction for atomic write
    let tx = conn.transaction().map_err(|e| {
        crate::errors::ApiErrorResponse {
            error_type: "DATABASE_ERROR".to_string(),
            message: format!("Failed to start transaction: {}", e),
        }
    })?;

    let existing = ConcessionRepository::get_in_tx(&tx, id, chrono::Utc::now())
        .map_err(|e| map_app_error(e))?;

    let mut concession = Concession::new(
        existing.cemetery_id,
        req.plot_id.or(existing.plot_id),
    );
    concession.id = id;
    concession.concession_number = req.concession_number.or(existing.concession_number);
    concession.concession_type =
        req.concession_type.unwrap_or(existing.concession_type);
    concession.duration_years =
        req.duration_years.unwrap_or(existing.duration_years);
    concession.start_date = req.start_date.unwrap_or(existing.start_date);
    concession.holder_first_name =
        req.holder_first_name.or(existing.holder_first_name);
    concession.holder_last_name = req.holder_last_name.or(existing.holder_last_name);
    concession.holder_address = req.holder_address.or(existing.holder_address);
    concession.holder_postal_code =
        req.holder_postal_code.or(existing.holder_postal_code);
    concession.holder_commune = req.holder_commune.or(existing.holder_commune);
    concession.observations = req.observations.or(existing.observations);
    concession.acquired_at = req.acquired_at.or(existing.acquired_at);
    concession.renewed_at = req.renewed_at.or(existing.renewed_at);
    concession.created_at = existing.created_at;

    ConcessionRepository::update_in_tx(&tx, id, &concession)
        .and_then(|result| {
            tx.commit()
                .map(|_| result)
                .map_err(|e| {
                    AppError::Database(e)
                })
        })
        .map_err(|e| map_app_error(e))
}

fn map_app_error(e: AppError) -> crate::errors::ApiErrorResponse {
    match e {
        AppError::NotFound(msg) => crate::errors::ApiErrorResponse {
            error_type: "NOT_FOUND".to_string(),
            message: msg,
        },
        AppError::InvalidInput(msg) => crate::errors::ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: msg,
        },
        AppError::Database(ref db_err) => {
            let err_str = db_err.to_string().to_lowercase();

            // Translate unique constraint violations to business errors.
            // The index idx_concessions_number_unique is an expression index, so SQLite can
            // reference it by name in the error message. Also check for the column name.
            if err_str.contains("unique constraint failed") {
                if err_str.contains("concession_number") || err_str.contains("idx_concessions_number_unique") {
                    return crate::errors::ApiErrorResponse {
                        error_type: "INVALID_INPUT".to_string(),
                        message: "A concession with this number already exists".to_string(),
                    };
                }
            }

            // Foreign key constraint violations should not reach here due to pre-validation
            // but handle them anyway as a fallback
            if err_str.contains("foreign key constraint failed") {
                return crate::errors::ApiErrorResponse {
                    error_type: "INVALID_INPUT".to_string(),
                    message: "A referenced entity does not exist".to_string(),
                };
            }

            // Default database error
            crate::errors::ApiErrorResponse {
                error_type: "DATABASE_ERROR".to_string(),
                message: format!("Database error: {}", db_err),
            }
        },
        AppError::Internal(msg) => crate::errors::ApiErrorResponse {
            error_type: "INTERNAL_ERROR".to_string(),
            message: msg,
        },
    }
}

fn validate_create_concession_request(conn: &std::sync::MutexGuard<rusqlite::Connection>, req: &CreateConcessionRequest) -> Result<(), crate::errors::ApiErrorResponse> {
    if req.cemetery_id <= 0 {
        return Err(crate::errors::ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: "cemetery_id must be a positive integer".to_string(),
        });
    }

    // Validate cemetery exists
    if let Err(AppError::NotFound(_)) = CemeteryRepository::get(conn, req.cemetery_id) {
        return Err(crate::errors::ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: format!("The specified cemetery with id {} does not exist", req.cemetery_id),
        });
    }

    // Validate plot exists (now mandatory)
    if req.plot_id <= 0 {
        return Err(crate::errors::ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: "plot_id must be a positive integer".to_string(),
        });
    }

    if let Err(AppError::NotFound(_)) = PlotRepository::get(conn, req.plot_id) {
        return Err(crate::errors::ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: format!("The specified plot with id {} does not exist", req.plot_id),
        });
    }

    // concession_number is mandatory
    if req.concession_number.trim().is_empty() {
        return Err(crate::errors::ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: "concession_number cannot be empty".to_string(),
        });
    }

    if req.concession_type.is_empty() {
        return Err(crate::errors::ApiErrorResponse {
            error_type: "INVALID_INPUT".to_string(),
            message: "concession_type is required".to_string(),
        });
    }

    Ok(())
}

fn validate_update_concession_request(conn: &std::sync::MutexGuard<rusqlite::Connection>, req: &UpdateConcessionRequest) -> Result<(), crate::errors::ApiErrorResponse> {
    // concession_number is Option<String>
    if let Some(num) = &req.concession_number {
        if num.trim().is_empty() {
            return Err(crate::errors::ApiErrorResponse {
                error_type: "INVALID_INPUT".to_string(),
                message: "concession_number cannot be empty if provided".to_string(),
            });
        }
    }

    // Validate plot exists if provided
    if let Some(plot_id) = req.plot_id {
        if let Err(AppError::NotFound(_)) = PlotRepository::get(conn, plot_id) {
            return Err(crate::errors::ApiErrorResponse {
                error_type: "INVALID_INPUT".to_string(),
                message: format!("The specified plot with id {} does not exist", plot_id),
            });
        }
    }

    Ok(())
}
