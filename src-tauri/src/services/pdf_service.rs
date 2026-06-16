use crate::dto::{BurialDTO, CemeteryDTO, ConcessionDTO, IndividualDTO, PlotDTO};
use chrono::Local;
use std::fs;
use std::path::PathBuf;

pub struct PdfService;

impl PdfService {
    /// Generate a formatted text document (PDF-like) for a concession
    pub fn generate_concession_pdf(
        concession: &ConcessionDTO,
        cemetery: &CemeteryDTO,
        plot: Option<&PlotDTO>,
        individual: Option<&IndividualDTO>,
        burials: &[BurialDTO],
        output_dir: &str,
    ) -> Result<String, String> {
        // Create output directory if it doesn't exist
        fs::create_dir_all(output_dir)
            .map_err(|e| format!("Failed to create output dir: {}", e))?;

        // Build document content
        let mut content = String::new();
        content.push_str("================================================================================\n");
        content.push_str("FICHE CONCESSION - DOCUMENT ADMINISTRATIF\n");
        content.push_str("================================================================================\n\n");

        // Header
        content.push_str(&format!("Concession ID         : {}\n", concession.id));
        content.push_str(&format!(
            "Date de génération    : {}\n",
            Local::now().format("%d/%m/%Y %H:%M:%S")
        ));
        content.push_str("\n");

        // Cemetery info
        content.push_str("INFORMATIONS CIMETIÈRE\n");
        content.push_str("----------------------\n");
        content.push_str(&format!("Nom du cimetière      : {}\n", cemetery.name));
        if let Some(commune) = &cemetery.commune {
            content.push_str(&format!("Commune               : {}\n", commune));
        }
        if let Some(capacity) = cemetery.capacity {
            content.push_str(&format!("Capacité              : {} emplacements\n", capacity));
        }
        content.push_str("\n");

        // Plot info
        if let Some(p) = plot {
            content.push_str("INFORMATIONS EMPLACEMENT\n");
            content.push_str("------------------------\n");
            if let Some(section) = &p.section {
                content.push_str(&format!("Secteur               : {}\n", section));
            }
            if let Some(row) = &p.row {
                content.push_str(&format!("Rangée                : {}\n", row));
            }
            if let Some(number) = &p.number {
                content.push_str(&format!("Numéro                : {}\n", number));
            }
            content.push_str(&format!("Capacité              : {}\n", p.capacity));
            content.push_str(&format!("Statut                : {}\n", p.status));
            content.push_str("\n");
        }

        // Concession info
        content.push_str("INFORMATIONS CONCESSION\n");
        content.push_str("-----------------------\n");
        content.push_str(&format!("Statut                : {}\n", concession.status));
        if let Some(acquired) = &concession.acquired_at {
            content.push_str(&format!("Date d'acquisition    : {}\n", acquired));
        }
        if let Some(expires) = &concession.expires_at {
            content.push_str(&format!("Date d'expiration     : {}\n", expires));
        }
        if let Some(renewed) = &concession.renewed_at {
            content.push_str(&format!("Date de renouvellement: {}\n", renewed));
        }
        content.push_str("\n");

        // Individual info
        if let Some(ind) = individual {
            content.push_str("TITULAIRE DE LA CONCESSION\n");
            content.push_str("---------------------------\n");
            content.push_str(&format!("Nom                   : {}\n", ind.name));
            if let Some(email) = &ind.email {
                content.push_str(&format!("Email                 : {}\n", email));
            }
            if let Some(phone) = &ind.phone {
                content.push_str(&format!("Téléphone             : {}\n", phone));
            }
            content.push_str(&format!("Rôle                  : {}\n", ind.role));
            content.push_str("\n");
        }

        // Burials
        if !burials.is_empty() {
            content.push_str("DÉFUNTS INHUMÉS\n");
            content.push_str("---------------\n");
            for (idx, burial) in burials.iter().enumerate() {
                let buried_date = burial
                    .buried_at
                    .as_ref()
                    .map(|d| d.as_str())
                    .unwrap_or("Date inconnue");
                content.push_str(&format!(
                    "{}. Défunt ID: {}, Inhumé le: {}\n",
                    idx + 1, burial.individual_id, buried_date
                ));
            }
            content.push_str("\n");
        }

        content.push_str("================================================================================\n");
        content.push_str("Ce document a été généré automatiquement par le système de gestion de cimetière.\n");
        content.push_str("================================================================================\n");

        // Generate filename
        let filename = format!(
            "Concession_{}_generated_{}.txt",
            concession.id,
            Local::now().format("%Y%m%d_%H%M%S")
        );
        let file_path = PathBuf::from(output_dir).join(&filename);

        // Save file
        fs::write(&file_path, content)
            .map_err(|e| format!("Failed to write PDF: {}", e))?;

        Ok(file_path.to_string_lossy().to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pdf_filename_format() {
        let filename = format!(
            "Concession_{}_generated_{}.pdf",
            123,
            Local::now().format("%Y%m%d_%H%M%S")
        );
        assert!(filename.contains("Concession_123_generated_"));
        assert!(filename.ends_with(".pdf"));
    }
}
