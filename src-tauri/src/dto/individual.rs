use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct IndividualDTO {
    pub id: i64,
    pub name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub role: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreateIndividualRequest {
    pub name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub role: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdateIndividualRequest {
    pub name: Option<String>,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub role: Option<String>,
}
