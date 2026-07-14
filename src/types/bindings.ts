// ============================================================
// AUTO-MIRRORED FROM src-tauri/src/dto/*.rs — DO NOT DIVERGE
// Update when Rust DTOs change. Target: replace with specta
// export when tauri-specta is fully wired (post MVP-06).
// ============================================================

// --- Cemetery ---

export interface CemeteryDTO {
  id: number;
  name: string;
  commune: string | null;
  capacity: number | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCemeteryRequest {
  name: string;
  commune?: string;
  capacity?: number;
}

export interface UpdateCemeteryRequest {
  name?: string;
  commune?: string;
  capacity?: number;
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

// --- Concession ---

export interface ConcessionDTO {
  id: number;
  cemetery_id: number;
  plot_id: number | null;
  acquired_at: string | null;
  expires_at: string | null;
  renewed_at: string | null;
  status: ConcessionStatus;
  created_at: string;
  updated_at: string;
}

export type ConcessionStatus =
  | "active"
  | "expiring_soon"
  | "expired"
  | "renewed"
  | "abandoned"
  | "reclaimed"
  | "archived";

export interface CreateConcessionRequest {
  cemetery_id: number;
  plot_id?: number;
  acquired_at?: string;
  expires_at?: string;
}

export interface UpdateConcessionRequest {
  plot_id?: number;
  acquired_at?: string;
  expires_at?: string;
  renewed_at?: string;
  status?: ConcessionStatus;
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
