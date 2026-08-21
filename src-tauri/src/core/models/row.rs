use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Row {
    pub id: i64,
    pub square_id: i64,
    pub normalized_code: String,
    pub display_label: String,
    pub display_order: i32,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}

impl Row {
    pub fn new(
        square_id: i64,
        normalized_code: String,
        display_label: String,
        display_order: i32,
    ) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            square_id,
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
    fn new_row_has_default_values() {
        let row = Row::new(1, "ROW_1".to_string(), "Row 1".to_string(), 0);

        assert_eq!(row.square_id, 1);
        assert_eq!(row.normalized_code, "ROW_1");
        assert_eq!(row.display_label, "Row 1");
        assert_eq!(row.display_order, 0);
        assert!(row.is_active);
        assert_eq!(row.id, 0);
    }

    #[test]
    fn row_can_be_serialized() {
        let row = Row::new(1, "ROW_1".to_string(), "Row 1".to_string(), 0);
        let json = serde_json::to_string(&row).unwrap();
        assert!(json.contains("ROW_1"));
    }
}
