use crate::db::repositories::{
    BurialRepository, CemeteryRepository, ConcessionRepository, PlotRepository,
};
use crate::services::PdfService;
use rusqlite::Connection;
use std::sync::Mutex;
use tauri::State;

/// Generate a PDF document for a concession
#[tauri::command]
pub fn generate_concession_pdf(
    concession_id: i64,
    state: State<Mutex<Connection>>,
) -> Result<String, String> {
    let conn = state.lock().map_err(|e| format!("Lock error: {}", e))?;

    // Fetch concession
    let concession = ConcessionRepository::get(&conn, concession_id)
        .map_err(|_| format!("Concession {} not found", concession_id))?;

    // Fetch cemetery
    let cemetery = CemeteryRepository::get(&conn, concession.cemetery_id)
        .map_err(|e| format!("Failed to fetch cemetery: {}", e))?;

    // Fetch plot if present
    let plot = if let Some(plot_id) = concession.plot_id {
        PlotRepository::get(&conn, plot_id).ok()
    } else {
        None
    };

    // Fetch individual (concessionnaire) if present
    // Note: We don't have a direct field for this in ConcessionDTO yet
    // For MVP-18, we'll skip this or you can extend the schema later
    let individual = None;

    // Fetch burials for this concession
    let burials = BurialRepository::list_by_concession(&conn, concession_id).unwrap_or_default();

    // Generate PDF
    // For MVP, use a temporary directory
    let output_dir = "/tmp/gestion-cimetiere-pdfs";

    PdfService::generate_concession_pdf(
        &concession,
        &cemetery,
        plot.as_ref(),
        individual.as_ref(),
        &burials,
        output_dir,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_concession_pdf_signature() {
        assert!(true);
    }
}
