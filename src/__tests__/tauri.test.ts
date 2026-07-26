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
  });
});
