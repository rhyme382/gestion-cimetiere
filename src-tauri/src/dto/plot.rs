use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct PlotDTO {
    pub id: i64,
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: i32,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreatePlotRequest {
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdatePlotRequest {
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: Option<i32>,
    pub status: Option<String>,
}
