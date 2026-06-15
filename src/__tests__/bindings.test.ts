import { describe, it, expect } from "vitest";
import type { CemeteryDTO, PlotDTO, ConcessionDTO, IndividualDTO } from "@/types/bindings";

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
      plot_id: null,
      acquired_at: null,
      expires_at: null,
      renewed_at: null,
      status: "active",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(example.status).toBe("active");
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
});
