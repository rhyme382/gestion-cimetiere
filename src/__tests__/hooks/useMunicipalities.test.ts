import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import {
  useMunicipalities,
  useMunicipality,
  createMunicipalityAsync,
  updateMunicipalityAsync,
  deleteMunicipalityAsync,
} from "@/hooks/useMunicipalities";
import * as tauriLib from "@/lib/tauri";
import type {
  MunicipalityDTO,
  CreateMunicipalityRequest,
  UpdateMunicipalityRequest,
} from "@/types/bindings";

vi.mock("@/lib/tauri");

describe("Municipality hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useMunicipalities", () => {
    it("should fetch and return municipalities list", async () => {
      const mockMunicipalities: MunicipalityDTO[] = [
        {
          id: 1,
          name: "Paris",
          insee_code: "75056",
          postal_code: "75001",
          email: "mairie@paris.fr",
          department: "75",
          region: "Île-de-France",
          notes: "Capitale",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ];

      vi.mocked(tauriLib.listMunicipalities).mockResolvedValue(
        mockMunicipalities
      );

      const { result } = renderHook(() => useMunicipalities());

      expect(result.current.loading).toBe(true);
      expect(result.current.data).toBeNull();

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toEqual(mockMunicipalities);
      expect(result.current.error).toBeNull();
      expect(tauriLib.listMunicipalities).toHaveBeenCalled();
    });

    it("should handle empty list", async () => {
      vi.mocked(tauriLib.listMunicipalities).mockResolvedValue([]);

      const { result } = renderHook(() => useMunicipalities());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toEqual([]);
      expect(result.current.error).toBeNull();
    });

    it("should handle fetch error", async () => {
      const testError = new Error("Fetch failed");
      vi.mocked(tauriLib.listMunicipalities).mockRejectedValue(testError);

      const { result } = renderHook(() => useMunicipalities());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toBeNull();
      expect(result.current.error).toEqual(testError);
    });

    it("should respect enabled option", () => {
      const { result } = renderHook(() => useMunicipalities({ enabled: false }));

      expect(result.current.loading).toBe(false);
      expect(tauriLib.listMunicipalities).not.toHaveBeenCalled();
    });

    it("should refetch municipalities", async () => {
      const mockMunicipalities: MunicipalityDTO[] = [
        {
          id: 1,
          name: "Paris",
          insee_code: "75056",
          postal_code: "75001",
          email: "mairie@paris.fr",
          department: "75",
          region: "Île-de-France",
          notes: "Capitale",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ];

      vi.mocked(tauriLib.listMunicipalities).mockResolvedValue(
        mockMunicipalities
      );

      const { result } = renderHook(() => useMunicipalities());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(tauriLib.listMunicipalities).toHaveBeenCalledTimes(1);

      await result.current.refetch();

      expect(tauriLib.listMunicipalities).toHaveBeenCalledTimes(2);
    });
  });

  describe("useMunicipality", () => {
    it("should fetch single municipality when id is provided", async () => {
      const mockMunicipality: MunicipalityDTO = {
        id: 1,
        name: "Paris",
        insee_code: "75056",
        postal_code: "75001",
        email: "mairie@paris.fr",
        department: "75",
        region: "Île-de-France",
        notes: "Capitale",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      vi.mocked(tauriLib.getMunicipality).mockResolvedValue(mockMunicipality);

      const { result } = renderHook(() => useMunicipality(1));

      expect(result.current.loading).toBe(true);

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toEqual(mockMunicipality);
      expect(result.current.error).toBeNull();
      expect(tauriLib.getMunicipality).toHaveBeenCalledWith(1);
    });

    it("should not fetch when id is null", () => {
      const { result } = renderHook(() => useMunicipality(null));

      expect(result.current.loading).toBe(false);
      expect(result.current.data).toBeNull();
      expect(tauriLib.getMunicipality).not.toHaveBeenCalled();
    });

    it("should respect enabled option", () => {
      const { result } = renderHook(() =>
        useMunicipality(1, { enabled: false })
      );

      expect(result.current.loading).toBe(false);
      expect(tauriLib.getMunicipality).not.toHaveBeenCalled();
    });

    it("should handle fetch error", async () => {
      const testError = new Error("Municipality not found");
      vi.mocked(tauriLib.getMunicipality).mockRejectedValue(testError);

      const { result } = renderHook(() => useMunicipality(999));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toBeNull();
      expect(result.current.error).toEqual(testError);
    });
  });

  describe("createMunicipalityAsync", () => {
    it("should create municipality successfully", async () => {
      const request: CreateMunicipalityRequest = {
        name: "Lyon",
        insee_code: "69123",
        postal_code: "69001",
        email: "mairie@lyon.fr",
        department: "69",
        region: "Auvergne-Rhône-Alpes",
        notes: "Deuxième ville",
      };

      const mockMunicipality: MunicipalityDTO = {
        id: 2,
        ...request,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      vi.mocked(tauriLib.createMunicipality).mockResolvedValue(
        mockMunicipality
      );

      const result = await createMunicipalityAsync(request);

      expect(result).toEqual(mockMunicipality);
      expect(tauriLib.createMunicipality).toHaveBeenCalledWith(request);
    });

    it("should propagate errors as Error objects", async () => {
      const testError = new Error("Validation error");
      vi.mocked(tauriLib.createMunicipality).mockRejectedValue(testError);

      await expect(createMunicipalityAsync({} as CreateMunicipalityRequest)).rejects.toThrow(
        "Validation error"
      );
    });

    it("should convert non-Error exceptions to Error", async () => {
      vi.mocked(tauriLib.createMunicipality).mockRejectedValue(
        "String error"
      );

      await expect(createMunicipalityAsync({} as CreateMunicipalityRequest)).rejects.toThrow(
        "String error"
      );
    });
  });

  describe("updateMunicipalityAsync", () => {
    it("should update municipality successfully", async () => {
      const updateRequest: UpdateMunicipalityRequest = {
        email: "contact@paris.fr",
        notes: "Email updated",
      };

      const mockUpdatedMunicipality: MunicipalityDTO = {
        id: 1,
        name: "Paris",
        insee_code: "75056",
        postal_code: "75001",
        email: "contact@paris.fr",
        department: "75",
        region: "Île-de-France",
        notes: "Email updated",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-02T00:00:00Z",
      };

      vi.mocked(tauriLib.updateMunicipality).mockResolvedValue(
        mockUpdatedMunicipality
      );

      const result = await updateMunicipalityAsync(1, updateRequest);

      expect(result).toEqual(mockUpdatedMunicipality);
      expect(tauriLib.updateMunicipality).toHaveBeenCalledWith(
        1,
        updateRequest
      );
    });

    it("should propagate errors as Error objects", async () => {
      const testError = new Error("Not found");
      vi.mocked(tauriLib.updateMunicipality).mockRejectedValue(testError);

      await expect(
        updateMunicipalityAsync(1, {} as UpdateMunicipalityRequest)
      ).rejects.toThrow("Not found");
    });
  });

  describe("deleteMunicipalityAsync", () => {
    it("should delete municipality successfully", async () => {
      vi.mocked(tauriLib.deleteMunicipality).mockResolvedValue(undefined);

      const result = await deleteMunicipalityAsync(1);

      expect(result).toBeUndefined();
      expect(tauriLib.deleteMunicipality).toHaveBeenCalledWith(1);
    });

    it("should propagate errors as Error objects", async () => {
      const testError = new Error("Cannot delete");
      vi.mocked(tauriLib.deleteMunicipality).mockRejectedValue(testError);

      await expect(deleteMunicipalityAsync(1)).rejects.toThrow(
        "Cannot delete"
      );
    });
  });
});
