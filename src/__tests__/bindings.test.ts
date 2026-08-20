import { describe, it, expect } from "vitest";
import type {
  MunicipalityDTO,
  CreateMunicipalityRequest,
  UpdateMunicipalityRequest,
  CemeteryDTO,
  PlotDTO,
  ConcessionDTO,
  IndividualDTO,
  DiagnosticDTO,
  ApiErrorResponse,
  ConcessionFilters,
  ConcessionType,
  ConcessionStatus,
  ErrorType,
  ConcessionError,
} from "@/types/bindings";

describe("Types bindings — cohérence de forme", () => {
  it("MunicipalityDTO a les champs attendus", () => {
    const example: MunicipalityDTO = {
      id: 1,
      name: "Paris",
      insee_code: "75056",
      postal_code: "75001",
      email: "mairie@paris.fr",
      department: "75",
      region: "Île-de-France",
      notes: "Capitale de la France",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.id).toBe(1);
    expect(example.name).toBe("Paris");
    expect(example.insee_code).toBe("75056");
    expect(example.postal_code).toBe("75001");
  });

  it("MunicipalityDTO peut avoir des champs optionnels null", () => {
    const example: MunicipalityDTO = {
      id: 2,
      name: "Petite Commune",
      insee_code: "12345",
      postal_code: null,
      email: null,
      department: null,
      region: null,
      notes: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.postal_code).toBeNull();
    expect(example.email).toBeNull();
    expect(example.department).toBeNull();
    expect(example.region).toBeNull();
    expect(example.notes).toBeNull();
  });

  it("CreateMunicipalityRequest valide le contrat de création", () => {
    const createReq: CreateMunicipalityRequest = {
      name: "Lyon",
      insee_code: "69123",
      postal_code: "69001",
      email: "mairie@lyon.fr",
      department: "69",
      region: "Auvergne-Rhône-Alpes",
      notes: "Deuxième ville de France",
    };
    expect(createReq.name).toBe("Lyon");
    expect(createReq.insee_code).toBe("69123");
    expect(createReq.postal_code).toBe("69001");
  });

  it("UpdateMunicipalityRequest valide le contrat de mise à jour partielle", () => {
    const updateReq1: UpdateMunicipalityRequest = {
      email: "contact@paris.fr",
    };
    expect(updateReq1.email).toBe("contact@paris.fr");
    expect(updateReq1.name).toBeUndefined();

    const updateReq2: UpdateMunicipalityRequest = {
      postal_code: null,
      notes: "Mise à jour informations",
    };
    expect(updateReq2.postal_code).toBeNull();
    expect(updateReq2.notes).toBe("Mise à jour informations");
  });

  it("CemeteryDTO a les champs attendus", () => {
    const example: CemeteryDTO = {
      id: 1,
      name: "Cimetière municipal",
      commune: null,
      capacity: null,
      municipality_id: 1,
      address: "123 rue de l'Église",
      is_active: 1,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.id).toBe(1);
    expect(example.name).toBe("Cimetière municipal");
    expect(example.municipality_id).toBe(1);
    expect(example.address).toBe("123 rue de l'Église");
    expect(example.is_active).toBe(1);
  });

  it("CemeteryDTO peut avoir municipality_id et address null", () => {
    const example: CemeteryDTO = {
      id: 2,
      name: "Cimetière distant",
      commune: "Marseille",
      capacity: 1000,
      municipality_id: null,
      address: null,
      is_active: 0,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.municipality_id).toBeNull();
    expect(example.address).toBeNull();
    expect(example.is_active).toBe(0);
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

  it("ErrorType énumère les codes d'erreur attendus", () => {
    const errorTypes: ErrorType[] = ["NOT_FOUND", "INVALID_INPUT", "DATABASE_ERROR", "INTERNAL_ERROR"];
    expect(errorTypes).toContain("NOT_FOUND");
    expect(errorTypes).toContain("INVALID_INPUT");
    expect(errorTypes).toContain("DATABASE_ERROR");
    expect(errorTypes).toContain("INTERNAL_ERROR");
  });

  it("ConcessionError étend ApiErrorResponse avec error_type typé", () => {
    const error: ConcessionError = {
      error_type: "INVALID_INPUT",
      message: "A concession with this number already exists",
    };
    expect(error.error_type).toBe("INVALID_INPUT");
    expect(error.message).toContain("concession");
  });

  it("ConcessionError gère les différents types d'erreur métier", () => {
    const notFoundError: ConcessionError = {
      error_type: "NOT_FOUND",
      message: "Concession not found",
    };
    expect(notFoundError.error_type).toBe("NOT_FOUND");

    const invalidInputError: ConcessionError = {
      error_type: "INVALID_INPUT",
      message: "cemetery_id must be a positive integer",
    };
    expect(invalidInputError.error_type).toBe("INVALID_INPUT");

    const databaseError: ConcessionError = {
      error_type: "DATABASE_ERROR",
      message: "Database error: constraint violation",
    };
    expect(databaseError.error_type).toBe("DATABASE_ERROR");
  });

  it("ConcessionDTO supporte les types TEMPORAIRE, TRENTENAIRE, CINQUANTENAIRE", () => {
    const temporaire: ConcessionDTO = {
      id: 10,
      cemetery_id: 1,
      plot_id: 1,
      concession_number: "TEMP-001",
      concession_type: "TEMPORAIRE",
      duration_years: 15,
      start_date: "2024-01-01",
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
    expect(temporaire.concession_type).toBe("TEMPORAIRE");
    expect(temporaire.duration_years).toBe(15);

    const trentenaire: ConcessionDTO = {
      ...temporaire,
      id: 11,
      concession_type: "TRENTENAIRE",
      duration_years: 30,
      expires_at: "2054-01-01",
    };
    expect(trentenaire.concession_type).toBe("TRENTENAIRE");
    expect(trentenaire.duration_years).toBe(30);

    const cinquantenaire: ConcessionDTO = {
      ...temporaire,
      id: 12,
      concession_type: "CINQUANTENAIRE",
      duration_years: 50,
      expires_at: "2074-01-01",
    };
    expect(cinquantenaire.concession_type).toBe("CINQUANTENAIRE");
    expect(cinquantenaire.duration_years).toBe(50);
  });

  it("PlotDTO gère les statuts available et occupied", () => {
    const availablePlot: PlotDTO = {
      id: 50,
      cemetery_id: 1,
      section: "B",
      row: 3,
      number: 10,
      capacity: 2,
      status: "available",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(availablePlot.status).toBe("available");

    const occupiedPlot: PlotDTO = {
      ...availablePlot,
      id: 51,
      status: "occupied",
    };
    expect(occupiedPlot.status).toBe("occupied");
  });

  it("ConcessionDTO peut représenter un renouvellement", () => {
    const renewed: ConcessionDTO = {
      id: 20,
      cemetery_id: 1,
      plot_id: 1,
      concession_number: "RENEW-001",
      concession_type: "PERPETUELLE",
      duration_years: null,
      start_date: "2024-01-01",
      holder_first_name: "Jean",
      holder_last_name: "Dupont",
      holder_address: "123 rue",
      holder_postal_code: "75001",
      holder_commune: "Paris",
      observations: "Renouvellée en 2024",
      acquired_at: "2024-01-01",
      expires_at: null,
      renewed_at: "2024-01-01",
      status: "PERPETUELLE",
      created_at: "2020-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(renewed.renewed_at).toBeDefined();
    expect(renewed.renewed_at).toBe("2024-01-01");
    expect(renewed.observations).toContain("Renouvellée");
  });

  it("CreateConcessionRequest valide le contrat de création", () => {
    const createReq: CreateConcessionRequest = {
      cemetery_id: 1,
      plot_id: 5,
      concession_number: "NEW-001",
      concession_type: "TRENTENAIRE",
      duration_years: 30,
      start_date: "2024-01-01",
      holder_first_name: "Alice",
      holder_last_name: "Martin",
      holder_address: "456 avenue",
      holder_postal_code: "75002",
      holder_commune: "Paris",
      observations: "Nouvelle concession",
    };
    expect(createReq.cemetery_id).toBe(1);
    expect(createReq.concession_type).toBe("TRENTENAIRE");
    expect(createReq.holder_first_name).toBe("Alice");
  });

  it("UpdateConcessionRequest valide le contrat de mise à jour partielle", () => {
    const updateReq1: UpdateConcessionRequest = {
      holder_first_name: "Robert",
    };
    expect(updateReq1.holder_first_name).toBe("Robert");
    expect(updateReq1.holder_last_name).toBeUndefined();

    const updateReq2: UpdateConcessionRequest = {
      holder_address: "789 rue",
      observations: "Mise à jour adresse",
    };
    expect(updateReq2.holder_address).toBe("789 rue");
    expect(updateReq2.observations).toContain("adresse");
  });

  it("ConcessionDTO avec null values pour champs optionnels", () => {
    const minimal: ConcessionDTO = {
      id: 99,
      cemetery_id: 1,
      plot_id: 1,
      concession_number: "MIN-001",
      concession_type: "PERPETUELLE",
      duration_years: null,
      start_date: "2024-01-01",
      holder_first_name: null,
      holder_last_name: null,
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
    expect(minimal.holder_first_name).toBeNull();
    expect(minimal.holder_last_name).toBeNull();
    expect(minimal.observations).toBeNull();
    expect(minimal.holder_address).toBeNull();
  });
});
