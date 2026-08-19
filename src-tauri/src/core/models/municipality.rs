use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Municipality {
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

impl Municipality {
    pub fn new(
        name: String,
        insee_code: String,
        postal_code: Option<String>,
        email: Option<String>,
    ) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            name,
            insee_code,
            postal_code,
            email,
            department: None,
            region: None,
            notes: None,
            created_at: now.clone(),
            updated_at: now,
        }
    }
}
