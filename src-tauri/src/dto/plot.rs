use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Type)]
pub struct HierarchicalPathDTO {
    pub section_id: Option<i64>,
    pub section_code: Option<String>,
    pub section_label: Option<String>,
    pub square_id: Option<i64>,
    pub square_code: Option<String>,
    pub square_label: Option<String>,
    pub row_id: Option<i64>,
    pub row_code: Option<String>,
    pub row_label: Option<String>,
}

impl Default for HierarchicalPathDTO {
    fn default() -> Self {
        Self {
            section_id: None,
            section_code: None,
            section_label: None,
            square_id: None,
            square_code: None,
            square_label: None,
            row_id: None,
            row_code: None,
            row_label: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct PlotDTO {
    pub id: i64,
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: i32,
    pub status: String,
    #[serde(default)]
    pub administrative_reference: Option<String>,
    #[serde(default)]
    pub hierarchical_path: Option<HierarchicalPathDTO>,
    pub created_at: String,
    pub updated_at: String,
}

impl Default for PlotDTO {
    fn default() -> Self {
        Self {
            id: 0,
            cemetery_id: 0,
            section: None,
            row: None,
            number: None,
            capacity: 0,
            status: String::new(),
            administrative_reference: None,
            hierarchical_path: None,
            created_at: String::new(),
            updated_at: String::new(),
        }
    }
}


#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreatePlotRequest {
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdatePlotRequest {
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: Option<i32>,
    pub status: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hierarchical_path_default_has_none_values() {
        let path = HierarchicalPathDTO::default();
        assert!(path.section_id.is_none());
        assert!(path.section_code.is_none());
        assert!(path.square_id.is_none());
        assert!(path.square_code.is_none());
        assert!(path.row_id.is_none());
        assert!(path.row_code.is_none());
    }

    #[test]
    fn plot_dto_with_administrative_reference() {
        let path = HierarchicalPathDTO {
            section_id: Some(1),
            section_code: Some("A".to_string()),
            section_label: Some("Section A".to_string()),
            square_id: Some(2),
            square_code: Some("001".to_string()),
            square_label: Some("Square 001".to_string()),
            row_id: Some(3),
            row_code: Some("1".to_string()),
            row_label: Some("Row 1".to_string()),
        };

        let plot = PlotDTO {
            id: 1,
            cemetery_id: 1,
            section: Some("A".to_string()),
            row: Some(1),
            number: Some(1),
            capacity: 1,
            status: "available".to_string(),
            administrative_reference: Some("EMP-001".to_string()),
            hierarchical_path: Some(path),
            created_at: "2024-01-01T00:00:00Z".to_string(),
            updated_at: "2024-01-01T00:00:00Z".to_string(),
        };

        assert_eq!(plot.id, 1);
        assert_eq!(plot.administrative_reference, Some("EMP-001".to_string()));
        assert!(plot.hierarchical_path.is_some());
    }

    #[test]
    fn plot_dto_preserves_historical_fields() {
        let plot = PlotDTO {
            id: 2,
            cemetery_id: 1,
            section: Some("B".to_string()),
            row: Some(5),
            number: Some(10),
            capacity: 2,
            status: "occupied".to_string(),
            administrative_reference: Some("EMP-002".to_string()),
            hierarchical_path: None,
            created_at: "2024-01-01T00:00:00Z".to_string(),
            updated_at: "2024-01-02T00:00:00Z".to_string(),
        };

        assert_eq!(plot.section, Some("B".to_string()));
        assert_eq!(plot.row, Some(5));
        assert_eq!(plot.number, Some(10));
        assert_eq!(plot.capacity, 2);
        assert_eq!(plot.status, "occupied");
    }

    #[test]
    fn plot_dto_serialization_includes_administrative_reference() {
        let plot = PlotDTO {
            id: 1,
            cemetery_id: 1,
            section: None,
            row: None,
            number: None,
            capacity: 1,
            status: "available".to_string(),
            administrative_reference: Some("EMP-001".to_string()),
            hierarchical_path: None,
            created_at: "2024-01-01T00:00:00Z".to_string(),
            updated_at: "2024-01-01T00:00:00Z".to_string(),
        };

        let json = serde_json::to_string(&plot).unwrap();
        assert!(json.contains("EMP-001"));
        assert!(json.contains("administrative_reference"));
    }
}
