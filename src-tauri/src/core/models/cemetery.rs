use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Cemetery {
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

impl Cemetery {
    pub fn new(name: String, commune: Option<String>, capacity: Option<i32>) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            name,
            commune,
            capacity,
            municipality_id: None,
            address: None,
            is_active: 1,
            created_at: now.clone(),
            updated_at: now,
        }
    }
}
