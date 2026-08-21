use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Square {
    pub id: i64,
    pub section_id: i64,
    pub normalized_code: String,
    pub display_label: String,
    pub display_order: i32,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}

impl Square {
    pub fn new(
        section_id: i64,
        normalized_code: String,
        display_label: String,
        display_order: i32,
    ) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            section_id,
            normalized_code,
            display_label,
            display_order,
            is_active: true,
            created_at: now.clone(),
            updated_at: now,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_square_has_default_values() {
        let square = Square::new(1, "SQUARE_1".to_string(), "Square 1".to_string(), 0);

        assert_eq!(square.section_id, 1);
        assert_eq!(square.normalized_code, "SQUARE_1");
        assert_eq!(square.display_label, "Square 1");
        assert_eq!(square.display_order, 0);
        assert!(square.is_active);
        assert_eq!(square.id, 0);
    }

    #[test]
    fn square_can_be_serialized() {
        let square = Square::new(1, "SQUARE_1".to_string(), "Square 1".to_string(), 0);
        let json = serde_json::to_string(&square).unwrap();
        assert!(json.contains("SQUARE_1"));
    }
}
