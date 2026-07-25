import { describe, it, expect } from "vitest";
import type { CemeteryDTO, PlotDTO, ConcessionDTO, IndividualDTO, DiagnosticDTO, ApiErrorResponse, ConcessionFilters, ConcessionType, ConcessionStatus } from "@/types/bindings";

describe("Types bindings — cohérence de forme", () => {
  it("CemeteryDTO a les champs attendus", () => {
    const example: CemeteryDTO = {
      id: 1,
      name: "Cimetière municipal",
      commune: null,
      capacity: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.id).toBe(1);
    expect(example.name).toBe("Cimetière municipal");
  });

  it("PlotDTO a les champs attendus", () => {
    const example: PlotDTO = {
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
    expect(example.status).toBe("available");
  });

  it("ConcessionDTO a les champs attendus", () => {
    const example: ConcessionDTO = {
      id: 1,
      cemetery_id: 1,
      plot_id: 1,
      concession_number: "CON-001",
      concession_type: "PERPETUELLE",
      duration_years: null,
      start_date: "2024-01-01T00:00:00Z",
      holder_first_name: "Jean",
      holder_last_name: "Dupont",
      holder_address: "123 Rue de l'Église",
      holder_postal_code: "75001",
      holder_commune: "Paris",
      observations: "Concession bien entretenue",
      acquired_at: "2024-01-01T00:00:00Z",
      expires_at: null,
      renewed_at: null,
      status: "PERPETUELLE",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.status).toBe("PERPETUELLE");
    expect(example.concession_number).toBe("CON-001");
    expect(example.concession_type).toBe("PERPETUELLE");
    expect(example.holder_first_name).toBe("Jean");
  });

  it("ConcessionDTO avec type TEMPORAIRE a duration_years", () => {
    const example: ConcessionDTO = {
      id: 2,
      cemetery_id: 1,
      plot_id: 2,
      concession_number: "CON-002",
      concession_type: "TEMPORAIRE",
      duration_years: 15,
      start_date: "2024-01-01T00:00:00Z",
      holder_first_name: "Marie",
      holder_last_name: "Martin",
      holder_address: null,
      holder_postal_code: null,
      holder_commune: null,
      observations: null,
      acquired_at: null,
      expires_at: "2039-01-01T00:00:00Z",
      renewed_at: null,
      status: "ACTIVE",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.duration_years).toBe(15);
    expect(example.expires_at).toBeDefined();
    expect(example.status).toBe("ACTIVE");
  });

  it("IndividualDTO a les champs attendus", () => {
    const example: IndividualDTO = {
      id: 1,
      name: "Jean Dupont",
      email: null,
      phone: null,
      role: "deceased",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.role).toBe("deceased");
  });

  it("DiagnosticDTO a les champs attendus", () => {
    const example: DiagnosticDTO = {
      health: "healthy",
      sqlite_available: true,
      app_version: "0.1.0",
      message: "Application is running normally",
    };
    expect(example.health).toBe("healthy");
    expect(example.sqlite_available).toBe(true);
    expect(example.app_version).toBe("0.1.0");
    expect(example.message).toContain("running");
  });

  it("DiagnosticDTO peut représenter un état dégradé", () => {
    const example: DiagnosticDTO = {
      health: "degraded",
      sqlite_available: false,
      app_version: "0.1.0",
      message: "SQLite connection check failed: Database locked",
    };
    expect(example.health).toBe("degraded");
    expect(example.sqlite_available).toBe(false);
    expect(example.message).toContain("SQLite");
  });

  it("ApiErrorResponse a les champs attendus", () => {
    const example: ApiErrorResponse = {
      error_type: "INVALID_INPUT",
      message: "A concession with this number already exists",
    };
    expect(example.error_type).toBe("INVALID_INPUT");
    expect(example.message).toContain("concession");
  });

  it("ConcessionFilters peuvent être partiels", () => {
    const filter1: ConcessionFilters = { cemetery_id: 1 };
    expect(filter1.cemetery_id).toBe(1);
    expect(filter1.status).toBeUndefined();

    const filter2: ConcessionFilters = { status: "EXPIREE" };
    expect(filter2.status).toBe("EXPIREE");
    expect(filter2.cemetery_id).toBeUndefined();

    const filter3: ConcessionFilters = { search: "Jean" };
    expect(filter3.search).toBe("Jean");
  });

  it("ConcessionType supporte les types métier", () => {
    const types: ConcessionType[] = ["TEMPORAIRE", "TRENTENAIRE", "CINQUANTENAIRE", "PERPETUELLE"];
    expect(types).toContain("TEMPORAIRE");
    expect(types).toContain("PERPETUELLE");
  });

  it("ConcessionStatus supporte les statuts calculés", () => {
    const statuses: ConcessionStatus[] = ["ACTIVE", "ECHEANCE_PROCHE", "EXPIREE", "PERPETUELLE"];
    expect(statuses).toContain("ACTIVE");
    expect(statuses).toContain("ECHEANCE_PROCHE");
  });
});
