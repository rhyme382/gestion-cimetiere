import { CemeteryMapDTO, PlotMapDTO } from "@/types/bindings";

/**
 * Mock data for CemeteryMap component (MVP-14 with no backend integration)
 * Respects PlotMapDTO structure defined in MVP-07
 */

export const mockPlots: PlotMapDTO[] = [
  // Section A - Row 1
  { id: 1, cemetery_id: 1, section: "A", row: 1, number: 1, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 2, cemetery_id: 1, section: "A", row: 1, number: 2, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 3, cemetery_id: 1, section: "A", row: 1, number: 3, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 4, cemetery_id: 1, section: "A", row: 1, number: 4, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 5, cemetery_id: 1, section: "A", row: 1, number: 5, status: "reserved", capacity: 1, occupied_count: 0, concession_count: 1 },
  { id: 6, cemetery_id: 1, section: "A", row: 1, number: 6, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 7, cemetery_id: 1, section: "A", row: 1, number: 7, status: "unavailable", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 8, cemetery_id: 1, section: "A", row: 1, number: 8, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },

  // Section A - Row 2
  { id: 9, cemetery_id: 1, section: "A", row: 2, number: 1, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 10, cemetery_id: 1, section: "A", row: 2, number: 2, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 11, cemetery_id: 1, section: "A", row: 2, number: 3, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 12, cemetery_id: 1, section: "A", row: 2, number: 4, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 13, cemetery_id: 1, section: "A", row: 2, number: 5, status: "reserved", capacity: 1, occupied_count: 0, concession_count: 1 },
  { id: 14, cemetery_id: 1, section: "A", row: 2, number: 6, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 15, cemetery_id: 1, section: "A", row: 2, number: 7, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 16, cemetery_id: 1, section: "A", row: 2, number: 8, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },

  // Section A - Row 3
  { id: 17, cemetery_id: 1, section: "A", row: 3, number: 1, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 18, cemetery_id: 1, section: "A", row: 3, number: 2, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 19, cemetery_id: 1, section: "A", row: 3, number: 3, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 20, cemetery_id: 1, section: "A", row: 3, number: 4, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 21, cemetery_id: 1, section: "A", row: 3, number: 5, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 22, cemetery_id: 1, section: "A", row: 3, number: 6, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 23, cemetery_id: 1, section: "A", row: 3, number: 7, status: "reserved", capacity: 1, occupied_count: 0, concession_count: 1 },
  { id: 24, cemetery_id: 1, section: "A", row: 3, number: 8, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },

  // Section B - Row 1
  { id: 25, cemetery_id: 1, section: "B", row: 1, number: 1, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 26, cemetery_id: 1, section: "B", row: 1, number: 2, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 27, cemetery_id: 1, section: "B", row: 1, number: 3, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 28, cemetery_id: 1, section: "B", row: 1, number: 4, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 29, cemetery_id: 1, section: "B", row: 1, number: 5, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 30, cemetery_id: 1, section: "B", row: 1, number: 6, status: "reserved", capacity: 1, occupied_count: 0, concession_count: 1 },

  // Section B - Row 2
  { id: 31, cemetery_id: 1, section: "B", row: 2, number: 1, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 32, cemetery_id: 1, section: "B", row: 2, number: 2, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 33, cemetery_id: 1, section: "B", row: 2, number: 3, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 34, cemetery_id: 1, section: "B", row: 2, number: 4, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
  { id: 35, cemetery_id: 1, section: "B", row: 2, number: 5, status: "occupied", capacity: 1, occupied_count: 1, concession_count: 1 },
  { id: 36, cemetery_id: 1, section: "B", row: 2, number: 6, status: "available", capacity: 1, occupied_count: 0, concession_count: 0 },
];

export const mockCemeteryMap: CemeteryMapDTO = {
  id: 1,
  name: "Cimetière municipal de Montfort",
  commune: "Montfort",
  plots: mockPlots,
  section_count: 2,
  max_row: 3,
  max_number: 8,
  total_capacity: 42,
  occupied_count: 16,
  available_count: 22,
};

/**
 * Create a smaller cemetery for testing specific scenarios
 */
export function createMockCemeteryMap(
  sectionCount: number = 1,
  rowCount: number = 2,
  plotsPerRow: number = 4
): CemeteryMapDTO {
  const plots: PlotMapDTO[] = [];
  let plotId = 1;
  let occupiedCount = 0;

  const statuses: Array<"available" | "occupied" | "reserved" | "unavailable"> = [
    "available",
    "occupied",
    "available",
    "reserved",
  ];

  for (let s = 0; s < sectionCount; s++) {
    const section = String.fromCharCode(65 + s); // A, B, C, ...
    for (let r = 1; r <= rowCount; r++) {
      for (let n = 1; n <= plotsPerRow; n++) {
        const status = statuses[(plotId - 1) % statuses.length];
        plots.push({
          id: plotId,
          cemetery_id: 1,
          section,
          row: r,
          number: n,
          status,
          capacity: 1,
          occupied_count: status === "occupied" ? 1 : 0,
          concession_count: status === "occupied" || status === "reserved" ? 1 : 0,
        });
        if (status === "occupied") occupiedCount++;
        plotId++;
      }
    }
  }

  return {
    id: 1,
    name: "Cimetière de test",
    commune: "Test",
    plots,
    section_count: sectionCount,
    max_row: rowCount,
    max_number: plotsPerRow,
    total_capacity: plots.length,
    occupied_count: occupiedCount,
    available_count: plots.length - occupiedCount,
  };
}
