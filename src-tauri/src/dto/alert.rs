use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Type, PartialEq)]
#[serde(rename_all = "UPPERCASE")]
pub enum AlertType {
    Critical,
    Warning,
    Info,
}

impl AlertType {
    pub fn threshold_days(&self) -> i32 {
        match self {
            AlertType::Critical => 30,
            AlertType::Warning => 90,
            AlertType::Info => 180,
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            AlertType::Critical => "CRITICAL",
            AlertType::Warning => "WARNING",
            AlertType::Info => "INFO",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "CRITICAL" => Some(AlertType::Critical),
            "WARNING" => Some(AlertType::Warning),
            "INFO" => Some(AlertType::Info),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct AlertDTO {
    pub id: i64,
    pub concession_id: i64,
    pub alert_type: AlertType,
    pub expected_expiry_date: String,
    pub days_until_expiry: i32,
    pub created_at: String,
    pub acknowledged_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct AlertSummaryDTO {
    pub total_alerts: i32,
    pub critical_count: i32,
    pub warning_count: i32,
    pub info_count: i32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_alert_type_serialization() {
        let critical = AlertType::Critical;
        assert_eq!(critical.threshold_days(), 30);

        let warning = AlertType::Warning;
        assert_eq!(warning.threshold_days(), 90);

        let info = AlertType::Info;
        assert_eq!(info.threshold_days(), 180);
    }

    #[test]
    fn test_alert_type_as_str() {
        assert_eq!(AlertType::Critical.as_str(), "CRITICAL");
        assert_eq!(AlertType::Warning.as_str(), "WARNING");
        assert_eq!(AlertType::Info.as_str(), "INFO");
    }

    #[test]
    fn test_alert_type_from_str() {
        assert_eq!(AlertType::from_str("CRITICAL"), Some(AlertType::Critical));
        assert_eq!(AlertType::from_str("WARNING"), Some(AlertType::Warning));
        assert_eq!(AlertType::from_str("INFO"), Some(AlertType::Info));
        assert_eq!(AlertType::from_str("INVALID"), None);
    }

    #[test]
    fn test_alert_dto_creation() {
        let alert = AlertDTO {
            id: 1,
            concession_id: 100,
            alert_type: AlertType::Critical,
            expected_expiry_date: "2026-07-15".to_string(),
            days_until_expiry: 29,
            created_at: "2026-06-16 10:00:00".to_string(),
            acknowledged_at: None,
        };

        assert_eq!(alert.concession_id, 100);
        assert_eq!(alert.days_until_expiry, 29);
        assert!(alert.acknowledged_at.is_none());
    }

    #[test]
    fn test_alert_summary_aggregation() {
        let summary = AlertSummaryDTO {
            total_alerts: 5,
            critical_count: 2,
            warning_count: 2,
            info_count: 1,
        };

        assert_eq!(summary.total_alerts, 5);
        assert_eq!(summary.critical_count, 2);
    }
}
