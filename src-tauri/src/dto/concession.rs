use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct ConcessionDTO {
    pub id: i64,
    pub cemetery_id: i64,
    pub plot_id: Option<i64>,
    pub acquired_at: Option<String>,
    pub expires_at: Option<String>,
    pub renewed_at: Option<String>,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreateConcessionRequest {
    pub cemetery_id: i64,
    pub plot_id: Option<i64>,
    pub acquired_at: Option<String>,
    pub expires_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdateConcessionRequest {
    pub plot_id: Option<i64>,
    pub acquired_at: Option<String>,
    pub expires_at: Option<String>,
    pub renewed_at: Option<String>,
    pub status: Option<String>,
}
