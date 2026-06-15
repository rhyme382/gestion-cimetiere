use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Cemetery {
    pub id: i64,
    pub name: String,
    pub commune: Option<String>,
    pub capacity: Option<i32>,
    pub created_at: String,
    pub updated_at: String,
}

impl Cemetery {
    pub fn new(name: String, commune: Option<String>, capacity: Option<i32>) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            name,
            commune,
            capacity,
            created_at: now.clone(),
            updated_at: now,
        }
    }
}
