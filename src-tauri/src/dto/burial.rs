use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct BurialDTO {
    pub id: i64,
    pub concession_id: i64,
    pub individual_id: i64,
    pub buried_at: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreateBurialRequest {
    pub concession_id: i64,
    pub individual_id: i64,
    pub buried_at: Option<String>,
}
