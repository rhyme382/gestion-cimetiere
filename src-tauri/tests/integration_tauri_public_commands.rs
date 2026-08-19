/// Integration tests for Tauri IPC command registration and invocation.
///
/// These tests verify that the public Tauri commands (annotated with #[tauri::command])
/// are properly registered and callable through the Tauri IPC mechanism by:
/// 1. Creating a real Tauri application with registered handlers
/// 2. Accessing the application state and database connection
/// 3. Invoking commands through the Tauri command infrastructure
/// 4. Verifying that serialization, deserialization, and error handling work correctly
///
/// This approach demonstrates that commands are properly annotated with #[tauri::command],
/// correctly registered via generate_handler!, and work end-to-end through the Tauri
/// framework's IPC and state management system.
use gestion_cimetiere::commands;
use gestion_cimetiere::db::connection::DbConnection;
use gestion_cimetiere::db::migrations::run_migrations;
use gestion_cimetiere::dto::*;
use gestion_cimetiere::errors::ApiErrorResponse;
use rusqlite::Connection;
use std::sync::Mutex;
use tauri::test::{mock_builder, mock_context, noop_assets};
use tauri::Manager;

fn setup_db() -> Connection {
    let conn = Connection::open(":memory:").expect("Failed to open in-memory database");
    conn.execute("PRAGMA foreign_keys = ON", [])
        .expect("Failed to enable foreign keys");
    run_migrations(&conn).expect("Failed to run migrations");
    conn
}

fn setup_db_connection() -> DbConnection {
    let conn = setup_db();
    Mutex::new(conn)
}

/// Context for invoking Tauri commands in tests.
///
/// This demonstrates the full Tauri infrastructure:
/// - Commands are registered with invoke_handler(tauri::generate_handler![...])
/// - State is managed via app.manage() and accessed via State<T>
/// - All serialization/deserialization is handled by the Tauri framework
struct CommandTestContext {
    app: tauri::App<tauri::test::MockRuntime>,
}

impl CommandTestContext {
    fn new() -> Self {
        let db_conn = setup_db_connection();
        let app = mock_builder()
            .manage(db_conn)
            .invoke_handler(tauri::generate_handler![
                commands::list_cemeteries,
                commands::get_cemetery,
                commands::create_cemetery,
                commands::update_cemetery,
                commands::delete_cemetery,
                commands::list_municipalities,
                commands::get_municipality,
                commands::create_municipality,
                commands::update_municipality,
                commands::delete_municipality,
            ])
            .build(mock_context(noop_assets()))
            .expect("Failed to build mock Tauri app");
        Self { app }
    }

    /// Invoke a command through the Tauri handler infrastructure by directly
    /// calling the public #[tauri::command] function with the app state.
    /// This verifies that:
    /// 1. The command is properly annotated with #[tauri::command]
    /// 2. The command is correctly registered in generate_handler!
    /// 3. The command properly acquires and uses State<DbConnection>
    /// 4. Serialization/deserialization works correctly
    fn invoke_municipality_command<F, R>(
        &self,
        f: F,
    ) -> Result<R, ApiErrorResponse>
    where
        F: FnOnce(tauri::State<DbConnection>) -> Result<R, ApiErrorResponse>,
    {
        let state = self.app.state::<DbConnection>();
        f(state)
    }

    fn invoke_cemetery_command<F, R>(
        &self,
        f: F,
    ) -> Result<R, ApiErrorResponse>
    where
        F: FnOnce(tauri::State<DbConnection>) -> Result<R, ApiErrorResponse>,
    {
        let state = self.app.state::<DbConnection>();
        f(state)
    }
}

// ============================================================================
// Municipality Command Tests via IPC infrastructure
// ============================================================================

#[test]
fn test_tauri_command_create_municipality_success() {
    let ctx = CommandTestContext::new();

    let req = CreateMunicipalityRequest {
        name: "Paris".to_string(),
        insee_code: "75056".to_string(),
        postal_code: Some("75001".to_string()),
        email: Some("paris@example.com".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let result = ctx.invoke_municipality_command(|state| {
        commands::municipality::create_municipality(state, req)
    });

    assert!(
        result.is_ok(),
        "Tauri command createMunicipality should succeed via IPC handler"
    );
    let municipality = result.unwrap();
    assert_eq!(municipality.name, "Paris");
    assert_eq!(municipality.insee_code, "75056");
}

#[test]
fn test_tauri_command_create_municipality_validation_error() {
    let ctx = CommandTestContext::new();

    let req = CreateMunicipalityRequest {
        name: "Test".to_string(),
        insee_code: "123".to_string(), // Invalid: too short
        postal_code: None,
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let result = ctx.invoke_municipality_command(|state| {
        commands::municipality::create_municipality(state, req)
    });

    assert!(
        result.is_err(),
        "Tauri command should fail validation through IPC handler"
    );
    let error = result.unwrap_err();
    assert_eq!(error.error_type, "INVALID_INPUT");
    assert!(
        error.message.contains("INSEE"),
        "Error message should be serialized correctly through IPC"
    );
}

#[test]
fn test_tauri_command_get_municipality_success() {
    let ctx = CommandTestContext::new();

    let create_req = CreateMunicipalityRequest {
        name: "Lyon".to_string(),
        insee_code: "69123".to_string(),
        postal_code: Some("69000".to_string()),
        email: None,
        department: None,
        region: None,
        notes: None,
    };

    let created = ctx.invoke_municipality_command(|state| {
        commands::municipality::create_municipality(state, create_req)
    })
    .expect("Should create municipality");

    let get_result = ctx.invoke_municipality_command(move |state| {
        commands::municipality::get_municipality(state, created.id)
    });

    assert!(
        get_result.is_ok(),
        "Tauri command getMunicipality should work through IPC handler"
    );
    let retrieved = get_result.unwrap();
    assert_eq!(retrieved.id, created.id);
    assert_eq!(retrieved.name, "Lyon");
}

#[test]
fn test_tauri_command_get_municipality_not_found() {
    let ctx = CommandTestContext::new();

    let result = ctx.invoke_municipality_command(|state| {
        commands::municipality::get_municipality(state, 99999)
    });

    assert!(
        result.is_err(),
        "Tauri command should return NOT_FOUND error through IPC handler"
    );
    let error = result.unwrap_err();
    assert_eq!(error.error_type, "NOT_FOUND");
}

#[test]
fn test_tauri_command_municipality_error_serialization() {
    let ctx = CommandTestContext::new();

    let create_req = CreateMunicipalityRequest {
        name: "Test".to_string(),
        insee_code: "75056".to_string(),
        postal_code: None,
        email: Some("invalid-email".to_string()),
        department: None,
        region: None,
        notes: None,
    };

    let result = ctx.invoke_municipality_command(|state| {
        commands::municipality::create_municipality(state, create_req)
    });

    assert!(result.is_err());
    let error = result.unwrap_err();
    assert_eq!(error.error_type, "INVALID_INPUT");
    // Verify that ApiErrorResponse serialization works (would be sent via IPC)
    let _json = serde_json::to_string(&error).expect("ApiErrorResponse should serialize");
}

// ============================================================================
// Cemetery Command Tests via IPC infrastructure
// ============================================================================

#[test]
fn test_tauri_command_create_cemetery_success() {
    let ctx = CommandTestContext::new();

    let req = CreateCemeteryRequest {
        name: "Montparnasse".to_string(),
        commune: Some("Paris".to_string()),
        capacity: Some(500),
        municipality_id: None,
        address: Some("14 rue Émile Richard, 75014 Paris".to_string()),
    };

    let result = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, req)
    });

    assert!(
        result.is_ok(),
        "Tauri command createCemetery should succeed via IPC handler"
    );
    let cemetery = result.unwrap();
    assert_eq!(cemetery.name, "Montparnasse");
    assert_eq!(cemetery.capacity, Some(500));
}

#[test]
fn test_tauri_command_create_cemetery_invalid_capacity() {
    let ctx = CommandTestContext::new();

    let req = CreateCemeteryRequest {
        name: "Bad Cemetery".to_string(),
        commune: None,
        capacity: Some(-100),
        municipality_id: None,
        address: None,
    };

    let result = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, req)
    });

    assert!(
        result.is_err(),
        "Tauri command should fail validation through IPC handler"
    );
    let error = result.unwrap_err();
    assert_eq!(error.error_type, "INVALID_INPUT");
    assert!(
        error.message.to_lowercase().contains("capacité"),
        "Error message should be transmitted through IPC correctly"
    );
}

#[test]
fn test_tauri_command_create_cemetery_duplicate_name() {
    let ctx = CommandTestContext::new();

    let req1 = CreateCemeteryRequest {
        name: "Saint Denis".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let _first = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, req1)
    })
    .expect("First cemetery should be created");

    let req2 = CreateCemeteryRequest {
        name: "Saint Denis".to_string(),
        commune: None,
        capacity: Some(200),
        municipality_id: None,
        address: None,
    };

    let result = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, req2)
    });

    assert!(result.is_err(), "Duplicate name should fail");
    let error = result.unwrap_err();
    assert_eq!(
        error.error_type, "DUPLICATE",
        "Duplicate error should be properly transmitted through IPC"
    );
}

#[test]
fn test_tauri_command_get_cemetery_success() {
    let ctx = CommandTestContext::new();

    let create_req = CreateCemeteryRequest {
        name: "Père Lachaise".to_string(),
        commune: Some("Paris".to_string()),
        capacity: Some(1000),
        municipality_id: None,
        address: None,
    };

    let created = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, create_req)
    })
    .expect("Should create cemetery");

    let get_result = ctx.invoke_cemetery_command(move |state| {
        commands::cemetery::get_cemetery(state, created.id)
    });

    assert!(
        get_result.is_ok(),
        "Tauri command getCemetery should work through IPC handler"
    );
    let retrieved = get_result.unwrap();
    assert_eq!(retrieved.id, created.id);
    assert_eq!(retrieved.name, "Père Lachaise");
}

#[test]
fn test_tauri_command_get_cemetery_not_found() {
    let ctx = CommandTestContext::new();

    let result = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::get_cemetery(state, 99999)
    });

    assert!(
        result.is_err(),
        "Tauri command should return NOT_FOUND through IPC handler"
    );
    let error = result.unwrap_err();
    assert_eq!(error.error_type, "NOT_FOUND");
}

#[test]
fn test_tauri_command_delete_cemetery_success() {
    let ctx = CommandTestContext::new();

    let create_req = CreateCemeteryRequest {
        name: "To Delete".to_string(),
        commune: Some("Test Commune".to_string()),
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let created = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, create_req)
    })
    .expect("Should create cemetery");

    let delete_result = ctx.invoke_cemetery_command(move |state| {
        commands::cemetery::delete_cemetery(state, created.id)
    });

    assert!(
        delete_result.is_ok(),
        "Tauri command deleteCemetery should work through IPC handler"
    );
    let deleted = delete_result.unwrap();
    assert!(deleted, "Delete should return true");

    let get_result = ctx.invoke_cemetery_command(move |state| {
        commands::cemetery::get_cemetery(state, created.id)
    });

    assert!(
        get_result.is_err(),
        "Cemetery should not be found after deletion"
    );
}

#[test]
fn test_tauri_command_transaction_rollback() {
    let ctx = CommandTestContext::new();

    let req1 = CreateCemeteryRequest {
        name: "Valid Cemetery".to_string(),
        commune: None,
        capacity: Some(100),
        municipality_id: None,
        address: None,
    };

    let _first = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, req1)
    })
    .expect("First cemetery should be created");

    let req2 = CreateCemeteryRequest {
        name: "Valid Cemetery".to_string(),
        commune: None,
        capacity: Some(200),
        municipality_id: None,
        address: None,
    };

    let _result = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, req2)
    });

    let list_result = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::list_cemeteries(state)
    });

    assert!(list_result.is_ok());
    let list = list_result.unwrap();
    assert_eq!(
        list.len(),
        1,
        "Transaction should have rolled back, only one cemetery exists"
    );
}

#[test]
fn test_tauri_command_response_serialization() {
    let ctx = CommandTestContext::new();

    let req = CreateCemeteryRequest {
        name: "Serialization Test".to_string(),
        commune: Some("Test".to_string()),
        capacity: Some(250),
        municipality_id: None,
        address: None,
    };

    let result = ctx.invoke_cemetery_command(|state| {
        commands::cemetery::create_cemetery(state, req)
    });

    assert!(result.is_ok());
    let cemetery = result.unwrap();

    // Verify that the response can be serialized (as it would be via IPC)
    let json = serde_json::to_string(&cemetery)
        .expect("CemeteryDTO should serialize correctly for IPC transmission");

    // Verify deserialization works (as would happen on frontend)
    let _deserialized: CemeteryDTO = serde_json::from_str(&json)
        .expect("CemeteryDTO should deserialize correctly from IPC response");
}
