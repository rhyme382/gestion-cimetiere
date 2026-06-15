use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Concession {
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

impl Concession {
    pub fn new(cemetery_id: i64, plot_id: Option<i64>) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            cemetery_id,
            plot_id,
            acquired_at: None,
            expires_at: None,
            renewed_at: None,
            status: "active".to_string(),
            created_at: now.clone(),
            updated_at: now,
        }
    }
}
