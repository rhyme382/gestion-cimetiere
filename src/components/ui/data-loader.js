import { jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
import { LoadingSpinner } from "./loading-spinner";
import { ErrorMessage } from "./error-message";
import { EmptyState } from "./empty-state";
export function DataLoader({ loading, error, data, children, onRetry, emptyState, }) {
    if (loading) {
        return _jsx(LoadingSpinner, { size: "md" });
    }
    if (error) {
        return _jsx(ErrorMessage, { error: error, onRetry: onRetry });
    }
    if (!data || (Array.isArray(data) && data.length === 0)) {
        if (emptyState) {
            return _jsx(EmptyState, { ...emptyState });
        }
        return null;
    }
    return _jsx(_Fragment, { children: children });
}
