use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Section {
    pub id: i64,
    pub cemetery_id: i64,
    pub normalized_code: String,
    pub display_label: String,
    pub display_order: i32,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}

impl Section {
    pub fn new(
        cemetery_id: i64,
        normalized_code: String,
        display_label: String,
        display_order: i32,
    ) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            cemetery_id,
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
    fn new_section_has_default_values() {
        let section = Section::new(1, "SECTION_A".to_string(), "Section A".to_string(), 0);

        assert_eq!(section.cemetery_id, 1);
        assert_eq!(section.normalized_code, "SECTION_A");
        assert_eq!(section.display_label, "Section A");
        assert_eq!(section.display_order, 0);
        assert!(section.is_active);
        assert_eq!(section.id, 0);
    }

    #[test]
    fn section_can_be_serialized() {
        let section = Section::new(1, "SECTION_A".to_string(), "Section A".to_string(), 0);
        let json = serde_json::to_string(&section).unwrap();
        assert!(json.contains("SECTION_A"));
    }
}
