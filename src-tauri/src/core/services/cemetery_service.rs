use rusqlite::Connection;
use crate::{dto::*, errors::AppResult};

pub struct CemeteryService;

impl CemeteryService {
    pub fn list_cemeteries(_conn: &Connection) -> AppResult<Vec<CemeteryDTO>> {
        // Stub implementation
        Ok(vec![])
    }

    pub fn create_cemetery(_conn: &Connection, _req: &CreateCemeteryRequest) -> AppResult<CemeteryDTO> {
        // Stub implementation
        Err(crate::errors::AppError::Internal("Not implemented".to_string()))
    }
}
