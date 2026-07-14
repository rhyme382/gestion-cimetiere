import { describe, it, expect, vi, beforeEach } from "vitest";
import { getDiagnostic } from "@/lib/tauri";
import type { DiagnosticDTO } from "@/types/bindings";

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
});
