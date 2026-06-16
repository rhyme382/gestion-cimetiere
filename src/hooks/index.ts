// Query hooks
export { useQuery, type UseQueryResult } from "./useQuery";
export { useCemeteries, useCemetery, createCemeteryAsync, updateCemeteryAsync, deleteCemeteryAsync } from "./useCemeteries";
export { usePlots, usePlot, createPlotAsync, updatePlotAsync } from "./usePlots";
export { useConcessions, useConcession, createConcessionAsync, updateConcessionAsync } from "./useConcessions";
export { useIndividuals, useIndividual, useSearchIndividuals, createIndividualAsync, updateIndividualAsync } from "./useIndividuals";
export { createBurialAsync } from "./useBurials";
export { useAlerts, useAlertSummary, refreshAlertsAsync, acknowledgeAlertAsync } from "./useAlerts";
export { usePdfGeneration } from "./usePdfGeneration";
