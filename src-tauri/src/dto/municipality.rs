use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct MunicipalityDTO {
    pub id: i64,
    pub name: String,
    pub insee_code: String,
    pub postal_code: Option<String>,
    pub email: Option<String>,
    pub department: Option<String>,
    pub region: Option<String>,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreateMunicipalityRequest {
    pub name: String,
    pub insee_code: String,
    pub postal_code: Option<String>,
    pub email: Option<String>,
    pub department: Option<String>,
    pub region: Option<String>,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdateMunicipalityRequest {
    pub name: Option<String>,
    pub insee_code: Option<String>,
    pub postal_code: Option<String>,
    pub email: Option<String>,
    pub department: Option<String>,
    pub region: Option<String>,
    pub notes: Option<String>,
}
