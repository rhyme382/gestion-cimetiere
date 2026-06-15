import { useState, useEffect } from "react";
export function useQuery(queryFn, options = {}) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { onSuccess, onError, enabled = true } = options;
    const fetchData = async () => {
        if (!enabled) {
            setLoading(false);
            return;
        }
        try {
            setLoading(true);
            setError(null);
            const result = await queryFn();
            setData(result);
            onSuccess?.(result);
        }
        catch (err) {
            const error = err instanceof Error ? err : new Error(String(err));
            setError(error);
            onError?.(error);
        }
        finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        fetchData();
    }, [enabled]);
    return {
        data,
        loading,
        error,
        refetch: fetchData,
    };
}
