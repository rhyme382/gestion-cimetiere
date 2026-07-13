use serde::{Deserialize, Serialize};
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct DiagnosticDTO {
    pub health: String,
    pub sqlite_available: bool,
    pub app_version: String,
    pub message: String,
}

impl DiagnosticDTO {
    pub fn new(
        health: String,
        sqlite_available: bool,
        app_version: String,
        message: String,
    ) -> Self {
        Self {
            health,
            sqlite_available,
            app_version,
            message,
        }
    }

    pub fn healthy(app_version: String) -> Self {
        Self {
            health: "healthy".to_string(),
            sqlite_available: true,
            app_version,
            message: "Application is running normally".to_string(),
        }
    }

    pub fn sqlite_error(app_version: String, error_msg: String) -> Self {
        Self {
            health: "degraded".to_string(),
            sqlite_available: false,
            app_version,
            message: format!("SQLite connection check failed: {}", error_msg),
        }
    }
}
