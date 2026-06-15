use rusqlite::Connection;
use crate::{core::models::Cemetery, dto::CemeteryDTO, errors::AppResult};

pub struct CemeteryRepository;

impl CemeteryRepository {
    pub fn list(_conn: &Connection) -> AppResult<Vec<CemeteryDTO>> {
        // Stub implementation
        Ok(vec![])
    }

    pub fn get(_conn: &Connection, id: i64) -> AppResult<CemeteryDTO> {
        // Stub implementation
        Err(crate::errors::AppError::NotFound(format!("Cemetery {}", id)))
    }

    pub fn create(_conn: &Connection, _cemetery: &Cemetery) -> AppResult<CemeteryDTO> {
        // Stub implementation
        Err(crate::errors::AppError::Internal("Not implemented".to_string()))
    }

    pub fn update(_conn: &Connection, _id: i64, _cemetery: &Cemetery) -> AppResult<CemeteryDTO> {
        // Stub implementation
        Err(crate::errors::AppError::Internal("Not implemented".to_string()))
    }

    pub fn delete(_conn: &Connection, _id: i64) -> AppResult<bool> {
        // Stub implementation
        Ok(false)
    }
}
