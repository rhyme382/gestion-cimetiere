use crate::errors::{AppError, AppResult};
use chrono::{DateTime, Datelike, NaiveDate, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ConcessionType {
    Temporaire,
    Trentenaire,
    Cinquantenaire,
    Perpetuelle,
}

impl ConcessionType {
    pub fn from_str(s: &str) -> AppResult<Self> {
        match s.to_uppercase().as_str() {
            "TEMPORAIRE" => Ok(ConcessionType::Temporaire),
            "TRENTENAIRE" => Ok(ConcessionType::Trentenaire),
            "CINQUANTENAIRE" => Ok(ConcessionType::Cinquantenaire),
            "PERPETUELLE" => Ok(ConcessionType::Perpetuelle),
            _ => Err(AppError::InvalidInput(format!(
                "Invalid concession type: {}",
                s
            ))),
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            ConcessionType::Temporaire => "TEMPORAIRE",
            ConcessionType::Trentenaire => "TRENTENAIRE",
            ConcessionType::Cinquantenaire => "CINQUANTENAIRE",
            ConcessionType::Perpetuelle => "PERPETUELLE",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ConcessionStatus {
    Active,
    SoonExpiring,
    Expired,
    Perpetuelle,
}

impl ConcessionStatus {
    pub fn from_str(s: &str) -> AppResult<Self> {
        match s.to_uppercase().as_str() {
            "ACTIVE" => Ok(ConcessionStatus::Active),
            "ECHEANCE_PROCHE" | "SOON_EXPIRING" | "SOONEXPIRING" => {
                Ok(ConcessionStatus::SoonExpiring)
            }
            "EXPIREE" | "EXPIRED" => Ok(ConcessionStatus::Expired),
            "PERPETUELLE" => Ok(ConcessionStatus::Perpetuelle),
            _ => Err(AppError::InvalidInput(format!(
                "Invalid concession status: {}",
                s
            ))),
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            ConcessionStatus::Active => "ACTIVE",
            ConcessionStatus::SoonExpiring => "ECHEANCE_PROCHE",
            ConcessionStatus::Expired => "EXPIREE",
            ConcessionStatus::Perpetuelle => "PERPETUELLE",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Concession {
    pub id: i64,
    pub cemetery_id: i64,
    pub plot_id: Option<i64>,
    pub concession_number: Option<String>,
    pub concession_type: String,
    pub duration_years: Option<i32>,
    pub start_date: Option<String>,
    pub holder_first_name: Option<String>,
    pub holder_last_name: Option<String>,
    pub holder_address: Option<String>,
    pub holder_postal_code: Option<String>,
    pub holder_commune: Option<String>,
    pub observations: Option<String>,
    pub acquired_at: Option<String>,
    /// Expiry date calculated automatically from start_date and duration_years.
    /// This is never set from user input; it is computed exclusively by the backend.
    pub expires_at: Option<String>,
    pub renewed_at: Option<String>,
    /// Status calculated automatically based on type and expiry date.
    /// This is never set from user input; it is computed exclusively by the backend.
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
}

impl Concession {
    pub fn new(cemetery_id: i64, plot_id: Option<i64>) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            id: 0,
            cemetery_id,
            plot_id,
            concession_number: None,
            concession_type: "PERPETUELLE".to_string(),
            duration_years: None,
            start_date: None,
            holder_first_name: None,
            holder_last_name: None,
            holder_address: None,
            holder_postal_code: None,
            holder_commune: None,
            observations: None,
            acquired_at: None,
            expires_at: None,
            renewed_at: None,
            status: "active".to_string(),
            created_at: now.clone(),
            updated_at: now,
        }
    }

    pub fn validate(&self) -> AppResult<()> {
        let concession_type = ConcessionType::from_str(&self.concession_type)?;
        // Validate start_date format whenever a value is provided.
        if let Some(start_date) = &self.start_date {
            NaiveDate::parse_from_str(start_date, "%Y-%m-%d").map_err(|_| {
                AppError::InvalidInput(format!(
                    "Invalid start_date format, expected YYYY-MM-DD: {}",
                    start_date
                ))
            })?;
        }

        match concession_type {
            ConcessionType::Temporaire => {
                if self.start_date.is_none() {
                    return Err(AppError::InvalidInput(
                        "Temporary concession must have a start_date".to_string(),
                    ));
                }
                match self.duration_years {
                    Some(duration) if duration >= 1 && duration <= 99 => Ok(()),
                    Some(duration) => Err(AppError::InvalidInput(format!(
                        "Temporary concessions must have a duration between 1 and 99 years, got {}",
                        duration
                    ))),
                    None => Err(AppError::InvalidInput(
                        "Temporary concession must have a duration_years".to_string(),
                    )),
                }
            }
            ConcessionType::Trentenaire => {
                if self.start_date.is_none() {
                    return Err(AppError::InvalidInput(
                        "30-year concession must have a start_date".to_string(),
                    ));
                }
                if self.duration_years != Some(30) {
                    Err(AppError::InvalidInput(
                        "30-year concession must have duration_years = 30".to_string(),
                    ))
                } else {
                    Ok(())
                }
            }
            ConcessionType::Cinquantenaire => {
                if self.start_date.is_none() {
                    return Err(AppError::InvalidInput(
                        "50-year concession must have a start_date".to_string(),
                    ));
                }
                if self.duration_years != Some(50) {
                    Err(AppError::InvalidInput(
                        "50-year concession must have duration_years = 50".to_string(),
                    ))
                } else {
                    Ok(())
                }
            }
            ConcessionType::Perpetuelle => {
                if self.start_date.is_none() {
                    return Err(AppError::InvalidInput(
                        "Perpetual concession must have a start_date".to_string(),
                    ));
                }
                if self.duration_years.is_some() {
                    Err(AppError::InvalidInput(
                        "Perpetual concession must not have duration_years".to_string(),
                    ))
                } else {
                    Ok(())
                }
            }
        }
    }

    pub fn calculate_expires_at(&self) -> AppResult<Option<String>> {
        let concession_type = ConcessionType::from_str(&self.concession_type)?;

        match concession_type {
            ConcessionType::Perpetuelle => Ok(None),
            _ => match (&self.start_date, &self.duration_years) {
                (Some(start_date_str), Some(duration)) => {
                    let start_date = NaiveDate::parse_from_str(start_date_str, "%Y-%m-%d")
                        .map_err(|_| {
                            AppError::InvalidInput(format!(
                                "Invalid start_date format, expected YYYY-MM-DD: {}",
                                start_date_str
                            ))
                        })?;

                    let target_year = start_date.year() + *duration as i32;

                    let expires_date = start_date
                        .with_year(target_year)
                        .or_else(|| {
                            if start_date.month() == 2 && start_date.day() == 29 {
                                let is_leap_year = (target_year % 4 == 0 && target_year % 100 != 0)
                                    || (target_year % 400 == 0);
                                if !is_leap_year {
                                    start_date
                                        .with_day(28)
                                        .and_then(|d| d.with_year(target_year))
                                } else {
                                    None
                                }
                            } else {
                                None
                            }
                        })
                        .unwrap_or_else(|| {
                            start_date
                                .with_year(target_year - 1)
                                .unwrap()
                                .with_month(12)
                                .unwrap()
                                .with_day(31)
                                .unwrap()
                        });

                    Ok(Some(expires_date.format("%Y-%m-%d").to_string()))
                }
                _ => Ok(None),
            },
        }
    }

    pub fn prepare_for_storage_at(&mut self, reference_date: DateTime<Utc>) -> AppResult<()> {
        self.validate()?;
        self.expires_at = self.calculate_expires_at()?;
        self.status = self.calculate_status(reference_date)?.as_str().to_owned();
        Ok(())
    }

    pub fn prepare_for_storage(&mut self) -> AppResult<()> {
        self.prepare_for_storage_at(Utc::now())
    }

    pub fn calculate_status(&self, reference_date: DateTime<Utc>) -> AppResult<ConcessionStatus> {
        let concession_type = ConcessionType::from_str(&self.concession_type)?;

        if concession_type == ConcessionType::Perpetuelle {
            return Ok(ConcessionStatus::Perpetuelle);
        }

        match &self.expires_at {
            None => Ok(ConcessionStatus::Active),
            Some(expires_at_str) => {
                let expires_at =
                    NaiveDate::parse_from_str(expires_at_str, "%Y-%m-%d").map_err(|_| {
                        AppError::InvalidInput(format!(
                            "Invalid expires_at format, expected YYYY-MM-DD: {}",
                            expires_at_str
                        ))
                    })?;

                let duration_until_expiry =
                    expires_at.signed_duration_since(reference_date.date_naive());
                let days_until_expiry = duration_until_expiry.num_days();

                if days_until_expiry < 0 {
                    Ok(ConcessionStatus::Expired)
                } else if days_until_expiry <= 366 {
                    Ok(ConcessionStatus::SoonExpiring)
                } else {
                    Ok(ConcessionStatus::Active)
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{TimeZone, Utc};

    fn concession(
        concession_type: &str,
        start_date: &str,
        duration_years: Option<i32>,
    ) -> Concession {
        let mut concession = Concession::new(1, Some(1));
        concession.concession_type = concession_type.to_string();
        concession.start_date = Some(start_date.to_string());
        concession.duration_years = duration_years;
        concession
    }

    #[test]
    fn validate_accepts_iso_civil_date() {
        let concession = concession("PERPETUELLE", "2026-08-14", None);

        assert!(concession.validate().is_ok());
    }

    #[test]
    fn validate_rejects_french_date_format() {
        let concession = concession("PERPETUELLE", "14/08/2026", None);

        assert!(concession.validate().is_err());
    }

    #[test]
    fn validate_rejects_rfc3339_timestamp() {
        let concession = concession("PERPETUELLE", "2026-08-14T00:00:00Z", None);

        assert!(concession.validate().is_err());
    }

    #[test]
    fn calculate_expires_at_uses_civil_date_format() {
        let concession = concession("TRENTENAIRE", "2026-08-14", Some(30));

        assert_eq!(
            concession.calculate_expires_at().unwrap(),
            Some("2056-08-14".to_string())
        );
    }

    #[test]
    fn calculate_expires_at_adjusts_leap_day() {
        let concession = concession("TEMPORAIRE", "2024-02-29", Some(1));

        assert_eq!(
            concession.calculate_expires_at().unwrap(),
            Some("2025-02-28".to_string())
        );
    }

    #[test]
    fn calculate_status_reports_active_soon_expiring_and_expired() {
        let reference_date = Utc.with_ymd_and_hms(2026, 8, 7, 12, 0, 0).single().unwrap();

        let mut active = concession("TEMPORAIRE", "2026-08-07", Some(2));
        active.expires_at = Some("2028-08-07".to_string());

        assert_eq!(
            active.calculate_status(reference_date).unwrap(),
            ConcessionStatus::Active
        );

        let mut soon_expiring = concession("TEMPORAIRE", "2025-08-08", Some(1));
        soon_expiring.expires_at = Some("2026-08-08".to_string());

        assert_eq!(
            soon_expiring.calculate_status(reference_date).unwrap(),
            ConcessionStatus::SoonExpiring
        );

        let mut expired = concession("TEMPORAIRE", "2025-08-06", Some(1));
        expired.expires_at = Some("2026-08-06".to_string());

        assert_eq!(
            expired.calculate_status(reference_date).unwrap(),
            ConcessionStatus::Expired
        );
    }

    #[test]
    fn prepare_for_storage_calculates_expiry_and_status() {
        let reference_date = Utc.with_ymd_and_hms(2026, 8, 7, 12, 0, 0).single().unwrap();

        let mut concession = concession("TRENTENAIRE", "2026-08-14", Some(30));

        concession.prepare_for_storage_at(reference_date).unwrap();

        assert_eq!(concession.expires_at.as_deref(), Some("2056-08-14"));
        assert_eq!(concession.status, "ACTIVE");
    }
}
