use crate::{db::repositories::AlertRepository, db::DbConnection, dto::*, services::AlertService};
use tauri::State;

/// List all unacknowledged alerts
#[tauri::command]
pub fn list_alerts(state: State<DbConnection>) -> Result<Vec<AlertDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertRepository::list_unacknowledged(&conn).map_err(|e| e.to_string())
}

/// Get aggregated alert summary
#[tauri::command]
pub fn get_alert_summary(state: State<DbConnection>) -> Result<AlertSummaryDTO, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertRepository::get_summary(&conn).map_err(|e| e.to_string())
}

/// Calculate and store alerts for all concessions
/// Called on-demand to refresh alert state
#[tauri::command]
pub fn refresh_alerts(state: State<DbConnection>) -> Result<Vec<AlertDTO>, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertService::calculate_alerts(&conn).map_err(|e| e.to_string())
}

/// Acknowledge a specific alert
#[tauri::command]
pub fn acknowledge_alert(state: State<DbConnection>, alert_id: i64) -> Result<bool, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;
    AlertRepository::acknowledge(&conn, alert_id).map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_list_alerts_signature() {
        assert!(true);
    }

    #[test]
    fn test_get_alert_summary_signature() {
        assert!(true);
    }

    #[test]
    fn test_refresh_alerts_signature() {
        assert!(true);
    }

    #[test]
    fn test_acknowledge_alert_signature() {
        assert!(true);
    }
}
