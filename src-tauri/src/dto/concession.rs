use crate::core::models::Concession;
use crate::errors::AppResult;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Deserializer, Serialize};

fn deserialize_double_option<'de, D, T>(deserializer: D) -> Result<Option<Option<T>>, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer).map(Some)
}
use specta::Type;

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct ConcessionDTO {
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
    pub expires_at: Option<String>,
    pub renewed_at: Option<String>,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreateConcessionRequest {
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
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdateConcessionRequest {
    pub plot_id: Option<i64>,
    pub concession_number: Option<String>,
    pub concession_type: Option<String>,
    #[serde(
        default,
        deserialize_with = "deserialize_double_option",
        skip_serializing_if = "Option::is_none"
    )]
    pub duration_years: Option<Option<i32>>,
    #[serde(
        default,
        deserialize_with = "deserialize_double_option",
        skip_serializing_if = "Option::is_none"
    )]
    pub start_date: Option<Option<String>>,
    pub holder_first_name: Option<String>,
    pub holder_last_name: Option<String>,
    pub holder_address: Option<String>,
    pub holder_postal_code: Option<String>,
    pub holder_commune: Option<String>,
    pub observations: Option<String>,
    pub acquired_at: Option<String>,
    pub renewed_at: Option<String>,
}

impl ConcessionDTO {
    pub fn with_calculated_status(mut self, reference_date: DateTime<Utc>) -> AppResult<Self> {
        let concession = Concession {
            id: self.id,
            cemetery_id: self.cemetery_id,
            plot_id: self.plot_id,
            concession_number: self.concession_number.clone(),
            concession_type: self.concession_type.clone(),
            duration_years: self.duration_years,
            start_date: self.start_date.clone(),
            holder_first_name: self.holder_first_name.clone(),
            holder_last_name: self.holder_last_name.clone(),
            holder_address: self.holder_address.clone(),
            holder_postal_code: self.holder_postal_code.clone(),
            holder_commune: self.holder_commune.clone(),
            observations: self.observations.clone(),
            acquired_at: self.acquired_at.clone(),
            expires_at: self.expires_at.clone(),
            renewed_at: self.renewed_at.clone(),
            status: self.status.clone(),
            created_at: self.created_at.clone(),
            updated_at: self.updated_at.clone(),
        };

        let calculated_status = concession.calculate_status(reference_date)?;
        self.status = calculated_status.as_str().to_owned();
        Ok(self)
    }
}

#[cfg(test)]
mod update_request_tests {
    use super::UpdateConcessionRequest;
    use serde_json::json;

    #[test]
    fn update_request_distinguishes_absent_null_and_value() {
        let absent: UpdateConcessionRequest = serde_json::from_value(json!({})).unwrap();
        assert_eq!(absent.duration_years, None);
        assert_eq!(absent.start_date, None);

        let cleared: UpdateConcessionRequest = serde_json::from_value(json!({
            "duration_years": null,
            "start_date": null
        }))
        .unwrap();
        assert_eq!(cleared.duration_years, Some(None));
        assert_eq!(cleared.start_date, Some(None));

        let provided: UpdateConcessionRequest = serde_json::from_value(json!({
            "duration_years": 30,
            "start_date": "2026-01-01T00:00:00Z"
        }))
        .unwrap();
        assert_eq!(provided.duration_years, Some(Some(30)));
        assert_eq!(
            provided.start_date,
            Some(Some("2026-01-01T00:00:00Z".to_string()))
        );
    }
}
