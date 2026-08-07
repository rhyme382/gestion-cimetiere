use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CemeteryDTO {
    pub id: i64,
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
    pub municipality_id: Option<i64>,
    pub address: Option<String>,
    pub is_active: i32,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreateCemeteryRequest {
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
    pub municipality_id: Option<i64>,
    pub address: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdateCemeteryRequest {
    pub name: Option<String>,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
    pub municipality_id: Option<i64>,
    pub address: Option<String>,
    pub is_active: Option<i32>,
}
