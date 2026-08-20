use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Plot {
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

impl Plot {
    pub fn new(
        cemetery_id: i64,
        section: Option<String>,
        row: Option<i32>,
        number: Option<i32>,
        capacity: i32,
    ) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            cemetery_id,
            section,
            row,
            number,
            capacity,
            status: "available".to_string(),
            created_at: now.clone(),
            updated_at: now,
        }
    }
}
