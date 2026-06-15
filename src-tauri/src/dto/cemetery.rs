use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CemeteryDTO {
    pub id: i64,
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreateCemeteryRequest {
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdateCemeteryRequest {
    pub name: Option<String>,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
}
