import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ConcessionCreatePage from "@/pages/ConcessionCreatePage";
import ConcessionEditPage from "@/pages/ConcessionEditPage";
import * as tauriLib from "@/lib/tauri";
import * as useConcessionHooks from "@/hooks/useConcessions";
import * as useCemeteriesHooks from "@/hooks/useCemeteries";
import * as usePlotsHooks from "@/hooks/usePlots";
import type { ConcessionDTO, CemeteryDTO, PlotDTO, ConcessionError } from "@/types/bindings";

vi.mock("@/lib/tauri");
vi.mock("@/hooks/useConcessions");
vi.mock("@/hooks/useCemeteries");
vi.mock("@/hooks/usePlots");

const mockCemetery: CemeteryDTO = {
  id: 1,
  name: "Cimetière du Père-Lachaise",
  commune: "Paris",
  capacity: 1000,
  created_at: "2020-01-01T10:00:00Z",
  updated_at: "2020-01-01T10:00:00Z",
};

const mockCemetery2: CemeteryDTO = {
  id: 2,
  name: "Cimetière Montmartre",
  commune: "Paris",
  capacity: 800,
  created_at: "2020-01-01T10:00:00Z",
  updated_at: "2020-01-01T10:00:00Z",
};

const mockPlots: PlotDTO[] = [
  {
    id: 10,
    cemetery_id: 1,
    section: "A",
    row: 5,
    number: 12,
    capacity: 2,
    status: "available",
    created_at: "2020-01-01T10:00:00Z",
    updated_at: "2020-01-01T10:00:00Z",
  },
  {
    id: 11,
    cemetery_id: 1,
    section: "A",
    row: 5,
    number: 13,
    capacity: 2,
    status: "available",
    created_at: "2020-01-01T10:00:00Z",
    updated_at: "2020-01-01T10:00:00Z",
  },
];

const mockConcession: ConcessionDTO = {
  id: 1,
  cemetery_id: 1,
  plot_id: 10,
  concession_number: "A-001",
  concession_type: "TRENTENAIRE",
  duration_years: 30,
  start_date: "2020-01-15",
  holder_first_name: "Jean",
  holder_last_name: "Dupont",
  holder_address: "123 rue de la Paix",
  holder_postal_code: "75001",
  holder_commune: "Paris",
  observations: "Concession bien entretenue",
  acquired_at: "2020-01-15",
  expires_at: "2050-01-15",
  renewed_at: null,
  status: "ACTIVE",
  created_at: "2020-01-15T10:00:00Z",
  updated_at: "2023-06-20T14:30:00Z",
};

describe("ConcessionCreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tauriLib.listPlots as any).mockResolvedValue(mockPlots);
    (useCemeteriesHooks.useCemeteries as any).mockReturnValue({
      data: [mockCemetery, mockCemetery2],
      loading: false,
      error: null,
      refetch: vi.fn(),
      isRefetching: false,
    });
  });

  it("renders form with required fields", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ConcessionCreatePage />
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/cimetière/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/emplacement/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/n° concession/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/type/i)).toBeInTheDocument();
  });

  it("loads plots when cemetery is selected", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ConcessionCreatePage />
      </MemoryRouter>
    );

    const cemeterySelect = await screen.findByLabelText(/cimetière/i);
    await user.selectOptions(cemeterySelect, "1");

    await waitFor(() => {
      expect(tauriLib.listPlots).toHaveBeenCalledWith(1);
    });

    const plotSelect = screen.getByLabelText(/emplacement/i);
    await waitFor(() => {
      expect(plotSelect).toHaveProperty("disabled", false);
    });
  });

  it("submits form with valid data", async () => {
    const user = userEvent.setup();
    const mockCreated = { ...mockConcession, id: 2 };
    (useConcessionHooks.createConcessionAsync as any).mockResolvedValueOnce(mockCreated);

    const navigateSpy = vi.fn();
    render(
      <MemoryRouter initialEntries={["/concessions/new"]}>
        <Routes>
          <Route path="/concessions/new" element={<ConcessionCreatePage />} />
          <Route path="/concessions/:id" element={<div>Detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Fill form
    const cemeterySelect = await screen.findByLabelText(/cimetière/i);
    await user.selectOptions(cemeterySelect, "1");

    const plotSelect = await screen.findByLabelText(/emplacement/i);
    await user.selectOptions(plotSelect, "10");

    const numberInput = screen.getByLabelText(/n° concession/i);
    await user.type(numberInput, "A-001");

    const typeSelect = screen.getByLabelText(/type/i);
    await user.selectOptions(typeSelect, "TRENTENAIRE");

    const startDateInput = screen.getByLabelText(/date de début/i);
    await user.type(startDateInput, "2020-01-15");

    const firstNameInput = screen.getByLabelText(/prénom/i);
    await user.type(firstNameInput, "Jean");

    const lastNameInput = screen.getByLabelText(/^Nom$/i);
    await user.type(lastNameInput, "Dupont");

    // Submit form
    const submitButton = screen.getByRole("button", { name: /créer/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(useConcessionHooks.createConcessionAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          cemetery_id: 1,
          plot_id: 10,
          concession_number: "A-001",
          concession_type: "TRENTENAIRE",
          start_date: "2020-01-15",
          holder_first_name: "Jean",
          holder_last_name: "Dupont",
        })
      );
    });
  });


  it("adapts duration field for different types", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ConcessionCreatePage />
      </MemoryRouter>
    );

    const typeSelect = await screen.findByLabelText(/type/i);

    // Initially TEMPORAIRE shows editable duration field
    await waitFor(() => {
      const durationInput = screen.getByLabelText(/durée \(années\)/i) as HTMLInputElement;
      expect(durationInput).toBeInTheDocument();
      expect(durationInput.type).toBe("number");
    });

    // Select TRENTENAIRE - should show read-only "30 ans"
    await user.selectOptions(typeSelect, "TRENTENAIRE");
    await waitFor(() => {
      expect(screen.queryByLabelText(/durée \(années\)/i)).not.toBeInTheDocument();
      // Check that the display-only "30 ans" div exists (not the option)
      const allLabels = screen.getAllByText(/durée/i);
      expect(allLabels.length).toBeGreaterThan(0);
    });

    // Select CINQUANTENAIRE - should show read-only "50 ans"
    await user.selectOptions(typeSelect, "CINQUANTENAIRE");
    await waitFor(() => {
      expect(screen.queryByLabelText(/durée \(années\)/i)).not.toBeInTheDocument();
    });

    // Select PERPETUELLE - should hide duration completely
    await user.selectOptions(typeSelect, "PERPETUELLE");
    await waitFor(() => {
      expect(screen.queryByLabelText(/durée/i)).not.toBeInTheDocument();
    });

    // Back to TEMPORAIRE - should show editable field again
    await user.selectOptions(typeSelect, "TEMPORAIRE");
    await waitFor(() => {
      const durationInput = screen.getByLabelText(/durée \(années\)/i) as HTMLInputElement;
      expect(durationInput).toBeInTheDocument();
      expect(durationInput.type).toBe("number");
    });
  });

  it("submits with fixed duration for TRENTENAIRE type", async () => {
    const user = userEvent.setup();
    const mockCreated = { ...mockConcession, id: 4, concession_type: "TRENTENAIRE", duration_years: 30 };
    (useConcessionHooks.createConcessionAsync as any).mockResolvedValueOnce(mockCreated);

    render(
      <MemoryRouter initialEntries={["/concessions/new"]}>
        <Routes>
          <Route path="/concessions/new" element={<ConcessionCreatePage />} />
          <Route path="/concessions/:id" element={<div>Detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    const cemeterySelect = await screen.findByLabelText(/cimetière/i);
    await user.selectOptions(cemeterySelect, "1");

    const plotSelect = await screen.findByLabelText(/emplacement/i);
    await user.selectOptions(plotSelect, "10");

    const numberInput = screen.getByLabelText(/n° concession/i);
    await user.type(numberInput, "A-003");

    const typeSelect = screen.getByLabelText(/type/i);
    await user.selectOptions(typeSelect, "TRENTENAIRE");

    const startDateInput = screen.getByLabelText(/date de début/i);
    await user.type(startDateInput, "2020-01-15");

    const lastNameInput = screen.getByLabelText(/^Nom$/i);
    await user.type(lastNameInput, "Dupont");

    const submitButton = screen.getByRole("button", { name: /créer/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(useConcessionHooks.createConcessionAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          concession_type: "TRENTENAIRE",
          duration_years: 30,
        })
      );
    });
  });

  it("submits with fixed duration for CINQUANTENAIRE type", async () => {
    const user = userEvent.setup();
    const mockCreated = { ...mockConcession, id: 5, concession_type: "CINQUANTENAIRE", duration_years: 50 };
    (useConcessionHooks.createConcessionAsync as any).mockResolvedValueOnce(mockCreated);

    render(
      <MemoryRouter initialEntries={["/concessions/new"]}>
        <Routes>
          <Route path="/concessions/new" element={<ConcessionCreatePage />} />
          <Route path="/concessions/:id" element={<div>Detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    const cemeterySelect = await screen.findByLabelText(/cimetière/i);
    await user.selectOptions(cemeterySelect, "1");

    const plotSelect = await screen.findByLabelText(/emplacement/i);
    await user.selectOptions(plotSelect, "10");

    const numberInput = screen.getByLabelText(/n° concession/i);
    await user.type(numberInput, "A-004");

    const typeSelect = screen.getByLabelText(/type/i);
    await user.selectOptions(typeSelect, "CINQUANTENAIRE");

    const startDateInput = screen.getByLabelText(/date de début/i);
    await user.type(startDateInput, "2020-01-15");

    const lastNameInput = screen.getByLabelText(/^Nom$/i);
    await user.type(lastNameInput, "Dupont");

    const submitButton = screen.getByRole("button", { name: /créer/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(useConcessionHooks.createConcessionAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          concession_type: "CINQUANTENAIRE",
          duration_years: 50,
        })
      );
    });
  });

  it("shows duration input field for TEMPORAIRE type", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ConcessionCreatePage />
      </MemoryRouter>
    );

    // Default type is TEMPORAIRE, which should show an editable duration input
    const durationInput = await screen.findByLabelText(/durée \(années\)/i) as HTMLInputElement;
    expect(durationInput).toBeInTheDocument();
    expect(durationInput.type).toBe("number");
    expect(durationInput).toHaveAttribute("min", "1");
    expect(durationInput).toHaveAttribute("max", "99");
  });

  it("preserves form values when switching cemeteries", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ConcessionCreatePage />
      </MemoryRouter>
    );

    const numberInput = screen.getByLabelText(/n° concession/i) as HTMLInputElement;
    await user.type(numberInput, "A-001");

    const cemeterySelect = await screen.findByLabelText(/cimetière/i);
    await user.selectOptions(cemeterySelect, "1");

    // Value should persist
    expect(numberInput.value).toBe("A-001");
  });

  it("allows creation without first name", async () => {
    const user = userEvent.setup();
    const mockCreated = { ...mockConcession, id: 3 };
    (useConcessionHooks.createConcessionAsync as any).mockResolvedValueOnce(mockCreated);

    render(
      <MemoryRouter initialEntries={["/concessions/new"]}>
        <Routes>
          <Route path="/concessions/new" element={<ConcessionCreatePage />} />
          <Route path="/concessions/:id" element={<div>Detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    const cemeterySelect = await screen.findByLabelText(/cimetière/i);
    await user.selectOptions(cemeterySelect, "1");

    const plotSelect = await screen.findByLabelText(/emplacement/i);
    await user.selectOptions(plotSelect, "10");

    const numberInput = screen.getByLabelText(/n° concession/i);
    await user.type(numberInput, "A-002");

    const typeSelect = screen.getByLabelText(/type/i);
    await user.selectOptions(typeSelect, "TRENTENAIRE");

    const startDateInput = screen.getByLabelText(/date de début/i);
    await user.type(startDateInput, "2020-01-15");

    const lastNameInput = screen.getByLabelText(/^Nom$/i);
    await user.type(lastNameInput, "Dupont");

    const submitButton = screen.getByRole("button", { name: /créer/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(useConcessionHooks.createConcessionAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          holder_last_name: "Dupont",
          holder_first_name: undefined,
        })
      );
    });
  });

  it("requires start_date and prevents submission when missing", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/concessions/new"]}>
        <Routes>
          <Route path="/concessions/new" element={<ConcessionCreatePage />} />
        </Routes>
      </MemoryRouter>
    );

    const cemeterySelect = await screen.findByLabelText(/cimetière/i);
    await user.selectOptions(cemeterySelect, "1");

    const plotSelect = await screen.findByLabelText(/emplacement/i);
    await user.selectOptions(plotSelect, "10");

    const numberInput = screen.getByLabelText(/n° concession/i);
    await user.type(numberInput, "A-005");

    const typeSelect = screen.getByLabelText(/type/i);
    await user.selectOptions(typeSelect, "TRENTENAIRE");

    const lastNameInput = screen.getByLabelText(/^Nom$/i);
    await user.type(lastNameInput, "Dupont");

    // Verify start_date field is present and required (marked with *)
    const startDateLabel = screen.getByLabelText(/date de début/i);
    expect(startDateLabel).toBeInTheDocument();

    // Do NOT fill start_date and attempt submission
    const submitButton = screen.getByRole("button", { name: /créer/i });
    await user.click(submitButton);

    // Wait a bit to ensure any async state updates complete
    await new Promise(resolve => setTimeout(resolve, 100));

    // Verify createConcessionAsync was NOT called (validation blocked it)
    expect(useConcessionHooks.createConcessionAsync).not.toHaveBeenCalled();
  });
});

describe("ConcessionEditPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tauriLib.listPlots as any).mockResolvedValue(mockPlots);
    (useConcessionHooks.useConcession as any).mockReturnValue({
      data: mockConcession,
      loading: false,
      error: null,
      refetch: vi.fn(),
      isRefetching: false,
    });

    (useCemeteriesHooks.useCemeteries as any).mockReturnValue({
      data: [mockCemetery, mockCemetery2],
      loading: false,
      error: null,
      refetch: vi.fn(),
      isRefetching: false,
    });
  });

  it("loads and displays existing concession data", async () => {
    render(
      <MemoryRouter initialEntries={["/concessions/1/edit"]}>
        <Routes>
          <Route path="/concessions/:id/edit" element={<ConcessionEditPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const numberInput = screen.getByDisplayValue("A-001") as HTMLInputElement;
      expect(numberInput).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue("Jean")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Dupont")).toBeInTheDocument();
  });

  it("submits updated data correctly", async () => {
    const user = userEvent.setup();
    (useConcessionHooks.updateConcessionAsync as any).mockResolvedValueOnce({
      ...mockConcession,
      holder_last_name: "Martin",
    });

    render(
      <MemoryRouter initialEntries={["/concessions/1/edit"]}>
        <Routes>
          <Route path="/concessions/:id/edit" element={<ConcessionEditPage />} />
          <Route path="/concessions/:id" element={<div>Detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for form to load
    const lastNameInput = await screen.findByDisplayValue("Dupont");

    // Change value
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Martin");

    // Submit
    const submitButton = screen.getByRole("button", { name: /mettre à jour/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(useConcessionHooks.updateConcessionAsync).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          holder_last_name: "Martin",
        })
      );
    });
  });


  it("shows cemetery as read-only", async () => {
    render(
      <MemoryRouter initialEntries={["/concessions/1/edit"]}>
        <Routes>
          <Route path="/concessions/:id/edit" element={<ConcessionEditPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const cemeteryLabel = screen.getByText(mockCemetery.name);
      expect(cemeteryLabel).toBeInTheDocument();
    });
  });

  it("shows fixed duration for TRENTENAIRE in edit form", async () => {
    render(
      <MemoryRouter initialEntries={["/concessions/1/edit"]}>
        <Routes>
          <Route path="/concessions/:id/edit" element={<ConcessionEditPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      // Verify that the duration input field is NOT present for TRENTENAIRE
      expect(screen.queryByLabelText(/durée \(années\)/i)).not.toBeInTheDocument();
      // Verify that a Label "Durée" exists
      const labels = screen.getAllByText(/durée/i);
      expect(labels.length).toBeGreaterThan(0);
    });
  });
});
