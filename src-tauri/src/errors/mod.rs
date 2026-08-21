use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NotFoundKind {
    Cemetery,
    Section,
    Square,
    Row,
    Plot,
    Concession,
    Individual,
    BurialOperation,
    Generic,
}

impl NotFoundKind {
    pub fn as_str(&self) -> &str {
        match self {
            NotFoundKind::Cemetery => "CEMETERY_NOT_FOUND",
            NotFoundKind::Section => "SECTION_NOT_FOUND",
            NotFoundKind::Square => "SQUARE_NOT_FOUND",
            NotFoundKind::Row => "ROW_NOT_FOUND",
            NotFoundKind::Plot => "PLOT_NOT_FOUND",
            NotFoundKind::Concession => "CONCESSION_NOT_FOUND",
            NotFoundKind::Individual => "INDIVIDUAL_NOT_FOUND",
            NotFoundKind::BurialOperation => "BURIAL_OPERATION_NOT_FOUND",
            NotFoundKind::Generic => "NOT_FOUND",
        }
    }
}

#[derive(Debug, Error)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Duplicate: {0}")]
    Duplicate(String),

    #[error("Internal server error: {0}")]
    Internal(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiErrorResponse {
    pub error_type: String,
    pub message: String,
}

impl serde::Serialize for AppError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        let (error_type, message) = match self {
            AppError::NotFound(msg) => {
                let kind = AppError::kind_from_message(msg);
                (kind.as_str().to_string(), msg.clone())
            }
            AppError::InvalidInput(msg) => ("INVALID_INPUT".to_string(), msg.clone()),
            AppError::Duplicate(msg) => ("DUPLICATE".to_string(), msg.clone()),
            AppError::Database(_) => (
                "DATABASE_ERROR".to_string(),
                "An unexpected database error occurred".to_string(),
            ),
            AppError::Internal(msg) => ("INTERNAL_ERROR".to_string(), msg.clone()),
        };

        ApiErrorResponse {
            error_type,
            message,
        }
        .serialize(serializer)
    }
}

impl AppError {
    pub fn with_kind(kind: NotFoundKind, message: impl Into<String>) -> Self {
        Self::NotFound(format!("[{}] {}", kind.as_str(), message.into()))
    }

    pub fn kind_from_message(message: &str) -> NotFoundKind {
        if message.starts_with("[CEMETERY_NOT_FOUND]") {
            NotFoundKind::Cemetery
        } else if message.starts_with("[SECTION_NOT_FOUND]") {
            NotFoundKind::Section
        } else if message.starts_with("[SQUARE_NOT_FOUND]") {
            NotFoundKind::Square
        } else if message.starts_with("[ROW_NOT_FOUND]") {
            NotFoundKind::Row
        } else if message.starts_with("[PLOT_NOT_FOUND]") {
            NotFoundKind::Plot
        } else if message.starts_with("[CONCESSION_NOT_FOUND]") {
            NotFoundKind::Concession
        } else if message.starts_with("[INDIVIDUAL_NOT_FOUND]") {
            NotFoundKind::Individual
        } else if message.starts_with("[BURIAL_OPERATION_NOT_FOUND]") {
            NotFoundKind::BurialOperation
        } else {
            NotFoundKind::Generic
        }
    }
}

pub type AppResult<T> = Result<T, AppError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn not_found_kind_as_str_returns_correct_values() {
        assert_eq!(NotFoundKind::Cemetery.as_str(), "CEMETERY_NOT_FOUND");
        assert_eq!(NotFoundKind::Section.as_str(), "SECTION_NOT_FOUND");
        assert_eq!(NotFoundKind::Square.as_str(), "SQUARE_NOT_FOUND");
        assert_eq!(NotFoundKind::Row.as_str(), "ROW_NOT_FOUND");
        assert_eq!(NotFoundKind::Plot.as_str(), "PLOT_NOT_FOUND");
    }

    #[test]
    fn app_error_with_kind_creates_typed_error() {
        let error = AppError::with_kind(NotFoundKind::Plot, "Plot 123 not found");
        if let AppError::NotFound(msg) = error {
            assert!(msg.contains("PLOT_NOT_FOUND"));
            assert!(msg.contains("Plot 123 not found"));
        } else {
            panic!("Expected NotFound error");
        }
    }

    #[test]
    fn app_error_kind_from_message_identifies_kind() {
        let msg = "[PLOT_NOT_FOUND] Plot 123 not found";
        assert_eq!(AppError::kind_from_message(msg), NotFoundKind::Plot);

        let msg = "[CEMETERY_NOT_FOUND] Cemetery 1 not found";
        assert_eq!(AppError::kind_from_message(msg), NotFoundKind::Cemetery);
    }

    #[test]
    fn app_error_serializes_to_api_response() {
        let error = AppError::with_kind(NotFoundKind::Plot, "Plot 123 not found");
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(response.error_type, "PLOT_NOT_FOUND");
        assert!(response.message.contains("PLOT_NOT_FOUND"));
    }

    #[test]
    fn app_error_serializes_cemetery_not_found_with_specific_type() {
        let error = AppError::with_kind(NotFoundKind::Cemetery, "Cemetery 1 not found");
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(response.error_type, "CEMETERY_NOT_FOUND");
    }

    #[test]
    fn app_error_serializes_section_not_found_with_specific_type() {
        let error = AppError::with_kind(NotFoundKind::Section, "Section A not found");
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(response.error_type, "SECTION_NOT_FOUND");
    }

    #[test]
    fn app_error_serializes_row_not_found_with_specific_type() {
        let error = AppError::with_kind(NotFoundKind::Row, "Row 5 not found");
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(response.error_type, "ROW_NOT_FOUND");
    }

    #[test]
    fn app_error_serializes_square_not_found_with_specific_type() {
        let error = AppError::with_kind(NotFoundKind::Square, "Square 001 not found");
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(response.error_type, "SQUARE_NOT_FOUND");
    }

    #[test]
    fn app_error_serializes_generic_not_found() {
        let error = AppError::NotFound("Resource not found".to_string());
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(response.error_type, "NOT_FOUND");
    }

    #[test]
    fn app_error_invalid_input_serializes() {
        let error = AppError::InvalidInput("Invalid value".to_string());
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(response.error_type, "INVALID_INPUT");
    }

    #[test]
    fn app_error_database_does_not_expose_raw_sqlite_message() {
        let sqlite_error = rusqlite::Error::SqliteFailure(
            rusqlite::ffi::Error::new(1),
            Some("table plots already exists".to_string()),
        );
        let error = AppError::Database(sqlite_error);
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();

        assert_eq!(response.error_type, "DATABASE_ERROR");
        assert_eq!(
            response.message,
            "An unexpected database error occurred"
        );
        assert!(!response.message.contains("sqlite"));
        assert!(!response.message.contains("table plots"));
    }

    #[test]
    fn app_error_database_serializes_with_safe_message() {
        let error = AppError::Database(rusqlite::Error::QueryReturnedNoRows);
        let json = serde_json::to_string(&error).unwrap();
        let response: ApiErrorResponse = serde_json::from_str(&json).unwrap();

        assert_eq!(response.error_type, "DATABASE_ERROR");
        assert_eq!(
            response.message,
            "An unexpected database error occurred"
        );
    }
}
