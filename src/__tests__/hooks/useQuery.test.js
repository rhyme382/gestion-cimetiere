import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useQuery } from "@/hooks/useQuery";
describe("useQuery", () => {
    it("returns data on success", async () => {
        const mockData = { id: 1, name: "Test" };
        const queryFn = vi.fn().mockResolvedValue(mockData);
        const { result } = renderHook(() => useQuery(queryFn));
        expect(result.current.loading).toBe(true);
        expect(result.current.data).toBeNull();
        await waitFor(() => {
            expect(result.current.loading).toBe(false);
        });
        expect(result.current.data).toEqual(mockData);
        expect(result.current.error).toBeNull();
    });
    it("handles errors", async () => {
        const testError = new Error("Test error");
        const queryFn = vi.fn().mockRejectedValue(testError);
        const { result } = renderHook(() => useQuery(queryFn));
        await waitFor(() => {
            expect(result.current.loading).toBe(false);
        });
        expect(result.current.data).toBeNull();
        expect(result.current.error).toEqual(testError);
    });
    it("respects enabled option", async () => {
        const queryFn = vi.fn();
        renderHook(() => useQuery(queryFn, { enabled: false }));
        expect(queryFn).not.toHaveBeenCalled();
    });
    it("calls onSuccess callback", async () => {
        const mockData = { id: 1 };
        const onSuccess = vi.fn();
        const queryFn = vi.fn().mockResolvedValue(mockData);
        renderHook(() => useQuery(queryFn, { onSuccess }));
        await waitFor(() => {
            expect(onSuccess).toHaveBeenCalledWith(mockData);
        });
    });
    it("calls onError callback", async () => {
        const testError = new Error("Test error");
        const onError = vi.fn();
        const queryFn = vi.fn().mockRejectedValue(testError);
        renderHook(() => useQuery(queryFn, { onError }));
        await waitFor(() => {
            expect(onError).toHaveBeenCalledWith(testError);
        });
    });
});
