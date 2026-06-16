use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Individual {
    pub id: i64,
    pub name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub role: String,
    pub created_at: String,
    pub updated_at: String,
}

impl Individual {
    pub fn new(name: String, email: Option<String>, phone: Option<String>, role: String) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            name,
            email,
            phone,
            role,
            created_at: now.clone(),
            updated_at: now,
        }
    }
}
