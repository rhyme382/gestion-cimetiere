// Query hooks
export { useQuery, type UseQueryResult, type UseQueryOptions } from "./useQuery";
export { useMunicipalities, useMunicipality, createMunicipalityAsync, updateMunicipalityAsync, deleteMunicipalityAsync } from "./useMunicipalities";
export { useCemeteries, useCemetery, createCemeteryAsync, updateCemeteryAsync, deleteCemeteryAsync } from "./useCemeteries";
export { usePlots, usePlot, createPlotAsync, updatePlotAsync } from "./usePlots";
export { useConcessions, useConcession, createConcessionAsync, updateConcessionAsync, getErrorMessage, isConcessionError } from "./useConcessions";
export { useIndividuals, useIndividual, useSearchIndividuals, createIndividualAsync, updateIndividualAsync } from "./useIndividuals";
export { createBurialAsync } from "./useBurials";
export { useAlerts, useAlertSummary, refreshAlertsAsync, acknowledgeAlertAsync } from "./useAlerts";
export { usePdfGeneration } from "./usePdfGeneration";
export { useBackups, type BackupInfo } from "./useBackups";

// Type exports for error handling and DTOs
export type {
  MunicipalityDTO, CreateMunicipalityRequest, UpdateMunicipalityRequest,
  ApiErrorResponse, ConcessionError, ErrorType, ApiError
} from "@/types/bindings";
