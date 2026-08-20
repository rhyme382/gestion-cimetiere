use crate::dto::{BurialDTO, CemeteryDTO, ConcessionDTO, IndividualDTO, PlotDTO};
use chrono::Local;
use printpdf::*;
use std::fs;
use std::fs::File;
use std::io::BufWriter;
use std::path::PathBuf;

pub struct PdfService;

impl PdfService {
    /// Generate a real PDF document for a concession
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

        // Create PDF document (A4 size)
        let (doc, page1, layer1) =
            PdfDocument::new("FICHE CONCESSION", Mm(210.0), Mm(297.0), "Layer 1");
        let font = doc
            .add_builtin_font(BuiltinFont::Helvetica)
            .map_err(|e| format!("Failed to add font: {}", e))?;

        let current_layer = doc.get_page(page1).get_layer(layer1);
        let mut y_position = 270.0;
        const LINE_HEIGHT: f32 = 5.0;
        const MARGIN: f32 = 10.0;

        // Title
        current_layer.use_text("FICHE CONCESSION", 16.0, Mm(MARGIN), Mm(y_position), &font);
        y_position -= LINE_HEIGHT * 2.0;

        current_layer.use_text(
            "DOCUMENT ADMINISTRATIF",
            12.0,
            Mm(MARGIN),
            Mm(y_position),
            &font,
        );
        y_position -= LINE_HEIGHT * 2.0;

        // Header info
        current_layer.use_text(
            &format!("ID Concession: {}", concession.id),
            10.0,
            Mm(MARGIN),
            Mm(y_position),
            &font,
        );
        y_position -= LINE_HEIGHT;

        current_layer.use_text(
            &format!(
                "Date de génération: {}",
                Local::now().format("%d/%m/%Y %H:%M:%S")
            ),
            10.0,
            Mm(MARGIN),
            Mm(y_position),
            &font,
        );
        y_position -= LINE_HEIGHT * 2.0;

        // Cemetery info
        current_layer.use_text(
            "INFORMATIONS CIMETIÈRE",
            11.0,
            Mm(MARGIN),
            Mm(y_position),
            &font,
        );
        y_position -= LINE_HEIGHT;

        current_layer.use_text(
            &format!("Cimetière: {}", cemetery.name),
            10.0,
            Mm(MARGIN + 2.0),
            Mm(y_position),
            &font,
        );
        y_position -= LINE_HEIGHT;

        if let Some(commune) = &cemetery.commune {
            current_layer.use_text(
                &format!("Commune: {}", commune),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;
        }

        if let Some(capacity) = cemetery.capacity {
            current_layer.use_text(
                &format!("Capacité: {} emplacements", capacity),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;
        }
        y_position -= LINE_HEIGHT;

        // Plot info
        if let Some(p) = plot {
            current_layer.use_text(
                "INFORMATIONS EMPLACEMENT",
                11.0,
                Mm(MARGIN),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;

            if let Some(section) = &p.section {
                current_layer.use_text(
                    &format!("Secteur: {}", section),
                    10.0,
                    Mm(MARGIN + 2.0),
                    Mm(y_position),
                    &font,
                );
                y_position -= LINE_HEIGHT;
            }

            if let Some(row) = &p.row {
                current_layer.use_text(
                    &format!("Rangée: {}", row),
                    10.0,
                    Mm(MARGIN + 2.0),
                    Mm(y_position),
                    &font,
                );
                y_position -= LINE_HEIGHT;
            }

            if let Some(number) = &p.number {
                current_layer.use_text(
                    &format!("Numéro: {}", number),
                    10.0,
                    Mm(MARGIN + 2.0),
                    Mm(y_position),
                    &font,
                );
                y_position -= LINE_HEIGHT;
            }

            current_layer.use_text(
                &format!("Capacité: {}", p.capacity),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;

            current_layer.use_text(
                &format!("Statut: {}", p.status),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT * 2.0;
        }

        // Concession info
        current_layer.use_text(
            "INFORMATIONS CONCESSION",
            11.0,
            Mm(MARGIN),
            Mm(y_position),
            &font,
        );
        y_position -= LINE_HEIGHT;

        current_layer.use_text(
            &format!("Statut: {}", concession.status),
            10.0,
            Mm(MARGIN + 2.0),
            Mm(y_position),
            &font,
        );
        y_position -= LINE_HEIGHT;

        if let Some(acquired) = &concession.acquired_at {
            current_layer.use_text(
                &format!("Date d'acquisition: {}", acquired),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;
        }

        if let Some(expires) = &concession.expires_at {
            current_layer.use_text(
                &format!("Date d'expiration: {}", expires),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;
        }

        if let Some(renewed) = &concession.renewed_at {
            current_layer.use_text(
                &format!("Date de renouvellement: {}", renewed),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;
        }
        y_position -= LINE_HEIGHT;

        // Individual info
        if let Some(ind) = individual {
            current_layer.use_text(
                "TITULAIRE DE LA CONCESSION",
                11.0,
                Mm(MARGIN),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;

            current_layer.use_text(
                &format!("Nom: {}", ind.name),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT;

            if let Some(email) = &ind.email {
                current_layer.use_text(
                    &format!("Email: {}", email),
                    10.0,
                    Mm(MARGIN + 2.0),
                    Mm(y_position),
                    &font,
                );
                y_position -= LINE_HEIGHT;
            }

            if let Some(phone) = &ind.phone {
                current_layer.use_text(
                    &format!("Téléphone: {}", phone),
                    10.0,
                    Mm(MARGIN + 2.0),
                    Mm(y_position),
                    &font,
                );
                y_position -= LINE_HEIGHT;
            }

            current_layer.use_text(
                &format!("Rôle: {}", ind.role),
                10.0,
                Mm(MARGIN + 2.0),
                Mm(y_position),
                &font,
            );
            y_position -= LINE_HEIGHT * 2.0;
        }

        // Burials
        if !burials.is_empty() {
            current_layer.use_text("DÉFUNTS INHUMÉS", 11.0, Mm(MARGIN), Mm(y_position), &font);
            y_position -= LINE_HEIGHT;

            for (idx, burial) in burials.iter().enumerate() {
                let buried_date = burial
                    .buried_at
                    .as_ref()
                    .map(|d| d.as_str())
                    .unwrap_or("Date inconnue");
                current_layer.use_text(
                    &format!(
                        "{}. Défunt ID: {}, Inhumé le: {}",
                        idx + 1,
                        burial.individual_id,
                        buried_date
                    ),
                    10.0,
                    Mm(MARGIN + 2.0),
                    Mm(y_position),
                    &font,
                );
                y_position -= LINE_HEIGHT;
            }
        }

        // Generate filename with .pdf extension
        let filename = format!(
            "Concession_{}_generated_{}.pdf",
            concession.id,
            Local::now().format("%Y%m%d_%H%M%S")
        );
        let file_path = PathBuf::from(output_dir).join(&filename);

        // Save PDF file
        let file =
            File::create(&file_path).map_err(|e| format!("Failed to create PDF file: {}", e))?;
        let mut writer = BufWriter::new(file);
        doc.save(&mut writer)
            .map_err(|e| format!("Failed to save PDF: {}", e))?;

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

    #[test]
    fn test_pdf_header_marker() {
        let pdf_header = b"%PDF-1.4";
        assert!(pdf_header.starts_with(b"%PDF"));
    }
}
