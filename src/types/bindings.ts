// ============================================================
// AUTO-MIRRORED FROM src-tauri/src/dto/*.rs — DO NOT DIVERGE
// Update when Rust DTOs change. Target: replace with specta
// export when tauri-specta is fully wired (post MVP-06).
// ============================================================

// --- Municipality ---

export interface MunicipalityDTO {
  id: number;
  name: string;
  insee_code: string;
  postal_code: string | null;
  email: string | null;
  department: string | null;
  region: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateMunicipalityRequest {
  name: string;
  insee_code: string;
  postal_code?: string;
  email?: string;
  department?: string;
  region?: string;
  notes?: string;
}

export interface UpdateMunicipalityRequest {
  name?: string;
  insee_code?: string;
  postal_code?: string | null;
  email?: string | null;
  department?: string | null;
  region?: string | null;
  notes?: string | null;
}

// --- Cemetery ---

export interface CemeteryDTO {
  id: number;
  name: string;
  commune: string | null;
  capacity: number | null;
  municipality_id: number | null;
  address: string | null;
  is_active: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCemeteryRequest {
  name: string;
  commune?: string;
  capacity?: number;
  municipality_id?: number;
  address?: string;
}

export interface UpdateCemeteryRequest {
  name?: string;
  commune?: string;
  capacity?: number;
  municipality_id?: number | null;
  address?: string | null;
  is_active?: number;
}

// --- Hierarchical Path (FP-004) ---

export interface HierarchicalPathDTO {
  section_id?: number | null;
  section_code?: string | null;
  section_label?: string | null;
  square_id?: number | null;
  square_code?: string | null;
  square_label?: string | null;
  row_id?: number | null;
  row_code?: string | null;
  row_label?: string | null;
}

// --- Section (FP-004) ---

export interface SectionDTO {
  id: number;
  cemetery_id: number;
  normalized_code: string;
  display_label: string;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Square / Carré (FP-004) ---

export interface SquareDTO {
  id: number;
  section_id: number;
  normalized_code: string;
  display_label: string;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Row / Rangée (FP-004) ---

export interface RowDTO {
  id: number;
  square_id: number;
  normalized_code: string;
  display_label: string;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Plot (Emplacement) ---

export interface PlotDTO {
  id: number;
  cemetery_id: number;
  section: string | null;
  row: number | null;
  number: number | null;
  capacity: number;
  status: PlotStatus;
  administrative_reference?: string | null;
  hierarchical_path?: HierarchicalPathDTO | null;
  created_at: string;
  updated_at: string;
}

export type PlotStatus = "available" | "occupied" | "reserved" | "unavailable";

export interface CreatePlotRequest {
  cemetery_id: number;
  section?: string;
  row?: number;
  number?: number;
  capacity: number;
}

export interface UpdatePlotRequest {
  section?: string;
  row?: number;
  number?: number;
  capacity?: number;
  status?: PlotStatus;
}

// --- Hierarchy List Types (tuples from Tauri commands) ---

export type SectionTuple = [id: number, code: string, label: string];
export type SquareTuple = [id: number, code: string, label: string];
export type RowTuple = [id: number, code: string, label: string];

// --- Concession ---

export type ConcessionType =
  | "TEMPORAIRE"
  | "TRENTENAIRE"
  | "CINQUANTENAIRE"
  | "PERPETUELLE";

export type ConcessionStatus =
  | "ACTIVE"
  | "ECHEANCE_PROCHE"
  | "EXPIREE"
  | "PERPETUELLE";

export interface ConcessionDTO {
  id: number;
  cemetery_id: number;
  plot_id: number | null;
  concession_number: string | null;
  concession_type: string;
  duration_years: number | null;
  start_date: string | null;
  holder_first_name: string | null;
  holder_last_name: string | null;
  holder_address: string | null;
  holder_postal_code: string | null;
  holder_commune: string | null;
  observations: string | null;
  acquired_at: string | null;
  expires_at: string | null;
  renewed_at: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateConcessionRequest {
  cemetery_id: number;
  plot_id: number;
  concession_number: string;
  concession_type: string;
  duration_years?: number;
  start_date?: string;
  holder_first_name?: string;
  holder_last_name?: string;
  holder_address?: string;
  holder_postal_code?: string;
  holder_commune?: string;
  observations?: string;
  acquired_at?: string;
}

export interface UpdateConcessionRequest {
  plot_id?: number;
  concession_number?: string;
  concession_type?: string;
  duration_years?: number | null;
  start_date?: string | null;
  holder_first_name?: string;
  holder_last_name?: string;
  holder_address?: string;
  holder_postal_code?: string;
  holder_commune?: string;
  observations?: string;
  acquired_at?: string;
  renewed_at?: string;
}

export interface ConcessionFilters {
  cemetery_id?: number;
  status?: ConcessionStatus;
  search?: string;
}

// --- Individual (Personne) ---

export interface IndividualDTO {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  role: IndividualRole;
  created_at: string;
  updated_at: string;
}

export type IndividualRole =
  | "deceased"
  | "concessionnaire"
  | "heir"
  | "contact";

export interface CreateIndividualRequest {
  name: string;
  email?: string;
  phone?: string;
  role: IndividualRole;
}

export interface UpdateIndividualRequest {
  name?: string;
  email?: string;
  phone?: string;
  role?: IndividualRole;
}

// --- Burial (Inhumation) ---

export interface BurialDTO {
  id: number;
  concession_id: number;
  individual_id: number;
  buried_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateBurialRequest {
  concession_id: number;
  individual_id: number;
  buried_at?: string;
}

// --- Cartography (MVP-07) ---

export interface PlotMapDTO {
  id: number;
  cemetery_id: number;
  section: string | null;
  row: number | null;
  number: number | null;
  status: PlotStatus;
  capacity: number;
  occupied_count: number;
  concession_count: number;
}

export interface CemeteryMapDTO {
  id: number;
  name: string;
  commune: string | null;
  plots: PlotMapDTO[];
  section_count: number;
  max_row: number;
  max_number: number;
  total_capacity: number;
  occupied_count: number;
  available_count: number;
}

export interface PlotLocationRequest {
  cemetery_id: number;
  section?: string;
  row?: number;
  number?: number;
}

// --- Alert (MVP-16/17) ---

export type AlertType = "CRITICAL" | "WARNING" | "INFO";

export interface AlertDTO {
  id: number;
  concession_id: number;
  alert_type: AlertType;
  expected_expiry_date: string;
  days_until_expiry: number;
  created_at: string;
  acknowledged_at: string | null;
}

export interface AlertSummaryDTO {
  total_alerts: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
}

// --- Diagnostic ---

export interface DiagnosticDTO {
  health: string;
  sqlite_available: boolean;
  app_version: string;
  message: string;
}

// --- Error Response ---

export interface ApiErrorResponse {
  error_type: string;
  message: string;
}

export type ErrorType =
  | "NOT_FOUND"
  | "INVALID_INPUT"
  | "DATABASE_ERROR"
  | "INTERNAL_ERROR";

export interface ConcessionError extends ApiErrorResponse {
  error_type: ErrorType;
}

export type ApiError = ApiErrorResponse | Error;
