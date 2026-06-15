use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Burial {
    pub id: i64,
    pub concession_id: i64,
    pub individual_id: i64,
    pub buried_at: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

impl Burial {
    pub fn new(concession_id: i64, individual_id: i64) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            concession_id,
            individual_id,
            buried_at: None,
            created_at: now.clone(),
            updated_at: now,
        }
    }
}
