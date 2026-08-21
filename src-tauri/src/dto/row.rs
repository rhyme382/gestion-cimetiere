use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct RowDTO {
    pub id: i64,
    pub square_id: i64,
    pub normalized_code: String,
    pub display_label: String,
    pub display_order: i32,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}
