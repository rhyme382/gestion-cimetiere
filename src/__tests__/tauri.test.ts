import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getDiagnostic,
  listConcessions,
  getConcession,
  createConcession,
  updateConcession,
  listCemeteries,
  getCemetery,
  createCemetery,
  updateCemetery,
  listIndividuals,
  getIndividual,
  createIndividual,
  updateIndividual,
  listPlots,
  getPlot,
  listAlerts,
  getAlertSummary,
} from "@/lib/tauri";
import type {
  DiagnosticDTO,
  ConcessionDTO,
  CreateConcessionRequest,
  UpdateConcessionRequest,
  CemeteryDTO,
  CreateCemeteryRequest,
  UpdateCemeteryRequest,
  IndividualDTO,
  CreateIndividualRequest,
  UpdateIndividualRequest,
} from "@/types/bindings";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

describe("Tauri client functions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getDiagnostic", () => {
    it("should be a function", () => {
      expect(typeof getDiagnostic).toBe("function");
    });

    it("should invoke get_diagnostic command with empty params", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockDiagnostic: DiagnosticDTO = {
        health: "healthy",
        sqlite_available: true,
        app_version: "0.1.0",
        message: "Application is running normally",
      };

      mockInvoke.mockResolvedValueOnce(mockDiagnostic);

      const result = await getDiagnostic();

      expect(mockInvoke).toHaveBeenCalledWith("get_diagnostic", {});
      expect(result).toEqual(mockDiagnostic);
      expect(result.health).toBe("healthy");
      expect(result.sqlite_available).toBe(true);
    });

    it("should handle degraded health status", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockDiagnostic: DiagnosticDTO = {
        health: "degraded",
        sqlite_available: false,
        app_version: "0.1.0",
        message: "SQLite connection check failed: Database locked",
      };

      mockInvoke.mockResolvedValueOnce(mockDiagnostic);

      const result = await getDiagnostic();

      expect(result.health).toBe("degraded");
      expect(result.sqlite_available).toBe(false);
      expect(result.message).toContain("SQLite");
    });

    it("should return DiagnosticDTO with correct shape", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockDiagnostic: DiagnosticDTO = {
        health: "healthy",
        sqlite_available: true,
        app_version: "0.1.0",
        message: "Application is running normally",
      };

      mockInvoke.mockResolvedValueOnce(mockDiagnostic);

      const result = await getDiagnostic();

      expect(result).toHaveProperty("health");
      expect(result).toHaveProperty("sqlite_available");
      expect(result).toHaveProperty("app_version");
      expect(result).toHaveProperty("message");

      expect(typeof result.health).toBe("string");
      expect(typeof result.sqlite_available).toBe("boolean");
      expect(typeof result.app_version).toBe("string");
      expect(typeof result.message).toBe("string");
    });
  });

  describe("Cemetery commands", () => {
    it("createCemetery should invoke create_cemetery with req parameter (not request)", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const req: CreateCemeteryRequest = {
        name: "Cimetière Municipal",
        commune: "Paris",
        capacity: 500,
      };

      const mockCemetery: CemeteryDTO = {
        id: 1,
        ...req,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockCemetery);

      const result = await createCemetery(req);

      expect(mockInvoke).toHaveBeenCalledWith("create_cemetery", { req });
      expect(result.id).toBe(1);
      expect(result.name).toBe("Cimetière Municipal");
    });

    it("updateCemetery should invoke update_cemetery with id and req parameters", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const updateReq: UpdateCemeteryRequest = {
        name: "Cimetière Rénové",
      };

      const mockCemetery: CemeteryDTO = {
        id: 1,
        name: "Cimetière Rénové",
        commune: "Paris",
        capacity: 500,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-02T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockCemetery);

      const result = await updateCemetery(1, updateReq);

      expect(mockInvoke).toHaveBeenCalledWith("update_cemetery", { id: 1, req: updateReq });
      expect(result.name).toBe("Cimetière Rénové");
    });
  });

  describe("Individual commands", () => {
    it("createIndividual should invoke create_individual with req parameter (not request)", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const req: CreateIndividualRequest = {
        name: "Jean Dupont",
        email: "jean@example.com",
        phone: "01234567890",
        role: "deceased",
      };

      const mockIndividual: IndividualDTO = {
        id: 1,
        ...req,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockIndividual);

      const result = await createIndividual(req);

      expect(mockInvoke).toHaveBeenCalledWith("create_individual", { req });
      expect(result.id).toBe(1);
      expect(result.name).toBe("Jean Dupont");
    });

    it("updateIndividual should invoke update_individual with id and req parameters", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const updateReq: UpdateIndividualRequest = {
        email: "newemail@example.com",
      };

      const mockIndividual: IndividualDTO = {
        id: 1,
        name: "Jean Dupont",
        email: "newemail@example.com",
        phone: "01234567890",
        role: "deceased",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-02T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockIndividual);

      const result = await updateIndividual(1, updateReq);

      expect(mockInvoke).toHaveBeenCalledWith("update_individual", { id: 1, req: updateReq });
      expect(result.email).toBe("newemail@example.com");
    });
  });

  describe("Concession commands", () => {
    it("listConcessions should invoke list_concessions without cemetery_id", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockConcessions: ConcessionDTO[] = [];
      mockInvoke.mockResolvedValueOnce(mockConcessions);

      const result = await listConcessions();

      expect(mockInvoke).toHaveBeenCalledWith("list_concessions", {});
      expect(result).toEqual([]);
    });

    it("listConcessions should invoke list_concessions with cemetery_id when provided", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockConcessions: ConcessionDTO[] = [];
      mockInvoke.mockResolvedValueOnce(mockConcessions);

      const result = await listConcessions(1);

      expect(mockInvoke).toHaveBeenCalledWith("list_concessions", { cemetery_id: 1 });
      expect(result).toEqual([]);
    });

    it("getConcession should invoke get_concession with id", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockConcession: ConcessionDTO = {
        id: 1,
        cemetery_id: 1,
        plot_id: 1,
        concession_number: "CON-001",
        concession_type: "PERPETUELLE",
        duration_years: null,
        start_date: "2024-01-01T00:00:00Z",
        holder_first_name: "Jean",
        holder_last_name: "Dupont",
        holder_address: null,
        holder_postal_code: null,
        holder_commune: null,
        observations: null,
        acquired_at: null,
        expires_at: null,
        renewed_at: null,
        status: "PERPETUELLE",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };
      mockInvoke.mockResolvedValueOnce(mockConcession);

      const result = await getConcession(1);

      expect(mockInvoke).toHaveBeenCalledWith("get_concession", { id: 1 });
      expect(result.id).toBe(1);
    });

    it("createConcession should invoke create_concession with req parameter", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const req: CreateConcessionRequest = {
        cemetery_id: 1,
        plot_id: 1,
        concession_number: "CON-001",
        concession_type: "PERPETUELLE",
        start_date: "2024-01-01T00:00:00Z",
        holder_first_name: "Jean",
        holder_last_name: "Dupont",
      };

      const mockConcession: ConcessionDTO = {
        id: 1,
        ...req,
        duration_years: null,
        holder_address: null,
        holder_postal_code: null,
        holder_commune: null,
        observations: null,
        acquired_at: null,
        expires_at: null,
        renewed_at: null,
        status: "PERPETUELLE",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockConcession);

      const result = await createConcession(req);

      expect(mockInvoke).toHaveBeenCalledWith("create_concession", { req });
      expect(result.id).toBe(1);
      expect(result.concession_number).toBe("CON-001");
    });

    it("updateConcession should invoke update_concession with id and req parameters", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const updateReq: UpdateConcessionRequest = {
        holder_first_name: "Jacques",
      };

      const mockConcession: ConcessionDTO = {
        id: 1,
        cemetery_id: 1,
        plot_id: 1,
        concession_number: "CON-001",
        concession_type: "PERPETUELLE",
        duration_years: null,
        start_date: "2024-01-01T00:00:00Z",
        holder_first_name: "Jacques",
        holder_last_name: "Dupont",
        holder_address: null,
        holder_postal_code: null,
        holder_commune: null,
        observations: null,
        acquired_at: null,
        expires_at: null,
        renewed_at: null,
        status: "PERPETUELLE",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockConcession);

      const result = await updateConcession(1, updateReq);

      expect(mockInvoke).toHaveBeenCalledWith("update_concession", { id: 1, req: updateReq });
      expect(result.holder_first_name).toBe("Jacques");
    });

    it("createConcession should support TEMPORAIRE type with duration_years", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const req: CreateConcessionRequest = {
        cemetery_id: 1,
        plot_id: 1,
        concession_number: "CON-TMP-001",
        concession_type: "TEMPORAIRE",
        duration_years: 15,
        start_date: "2024-01-01",
      };

      const mockConcession: ConcessionDTO = {
        id: 2,
        ...req,
        holder_first_name: null,
        holder_last_name: null,
        holder_address: null,
        holder_postal_code: null,
        holder_commune: null,
        observations: null,
        acquired_at: null,
        expires_at: "2039-01-01",
        renewed_at: null,
        status: "ACTIVE",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockConcession);

      const result = await createConcession(req);

      expect(result.duration_years).toBe(15);
      expect(result.expires_at).toBe("2039-01-01");
      expect(result.status).toBe("ACTIVE");
    });

    it("getConcession should handle concession with ECHEANCE_PROCHE status", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockConcession: ConcessionDTO = {
        id: 3,
        cemetery_id: 1,
        plot_id: 1,
        concession_number: "CON-002",
        concession_type: "TRENTENAIRE",
        duration_years: 30,
        start_date: "2020-01-01",
        holder_first_name: "Marie",
        holder_last_name: "Martin",
        holder_address: "456 avenue",
        holder_postal_code: "75002",
        holder_commune: "Paris",
        observations: null,
        acquired_at: "2020-01-01",
        expires_at: "2050-01-01",
        renewed_at: null,
        status: "ECHEANCE_PROCHE",
        created_at: "2020-01-01T00:00:00Z",
        updated_at: "2023-06-20T14:30:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockConcession);

      const result = await getConcession(3);

      expect(result.status).toBe("ECHEANCE_PROCHE");
      expect(result.expires_at).toBe("2050-01-01");
    });

    it("getConcession should handle concession with EXPIREE status", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockConcession: ConcessionDTO = {
        id: 4,
        cemetery_id: 1,
        plot_id: 1,
        concession_number: "CON-003",
        concession_type: "CINQUANTENAIRE",
        duration_years: 50,
        start_date: "2010-01-01",
        holder_first_name: "Pierre",
        holder_last_name: "Bernard",
        holder_address: null,
        holder_postal_code: null,
        holder_commune: null,
        observations: null,
        acquired_at: null,
        expires_at: "2060-01-01",
        renewed_at: null,
        status: "EXPIREE",
        created_at: "2010-01-01T00:00:00Z",
        updated_at: "2010-01-01T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockConcession);

      const result = await getConcession(4);

      expect(result.status).toBe("EXPIREE");
      expect(result.expires_at).toBe("2060-01-01");
    });
  });

  describe("Plot commands", () => {
    it("listPlots should invoke list_plots with cemetery_id", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockPlotsData: PlotDTO[] = [];
      mockInvoke.mockResolvedValueOnce(mockPlotsData);

      const result = await listPlots(1);

      expect(mockInvoke).toHaveBeenCalledWith("list_plots", { cemetery_id: 1 });
      expect(result).toEqual([]);
    });

    it("getPlot should invoke get_plot with id", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockPlotData: PlotDTO = {
        id: 1,
        cemetery_id: 1,
        section: "A",
        row: 1,
        number: 5,
        capacity: 2,
        status: "available",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      mockInvoke.mockResolvedValueOnce(mockPlotData);

      const result = await getPlot(1);

      expect(mockInvoke).toHaveBeenCalledWith("get_plot", { id: 1 });
      expect(result.id).toBe(1);
      expect(result.section).toBe("A");
    });
  });

  describe("Alert commands", () => {
    it("listAlerts should invoke list_alerts", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockAlertsData = [];
      mockInvoke.mockResolvedValueOnce(mockAlertsData);

      const result = await listAlerts();

      expect(mockInvoke).toHaveBeenCalledWith("list_alerts");
      expect(result).toEqual([]);
    });

    it("getAlertSummary should invoke get_alert_summary", async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      const mockInvoke = invoke as ReturnType<typeof vi.fn>;

      const mockSummaryData = {
        total_alerts: 5,
        critical_count: 2,
        warning_count: 3,
        info_count: 0,
      };

      mockInvoke.mockResolvedValueOnce(mockSummaryData);

      const result = await getAlertSummary();

      expect(mockInvoke).toHaveBeenCalledWith("get_alert_summary");
      expect(result).toEqual(mockSummaryData);
    });
  });
});
