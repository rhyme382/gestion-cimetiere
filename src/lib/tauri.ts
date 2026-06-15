import { invoke } from "@tauri-apps/api/core";
import type {
  CemeteryDTO, CreateCemeteryRequest, UpdateCemeteryRequest,
  PlotDTO, CreatePlotRequest, UpdatePlotRequest,
  ConcessionDTO, CreateConcessionRequest, UpdateConcessionRequest,
  IndividualDTO, CreateIndividualRequest, UpdateIndividualRequest,
  BurialDTO, CreateBurialRequest,
} from "@/types/bindings";

// Cemetery
export const listCemeteries = () => invoke<CemeteryDTO[]>("list_cemeteries");
export const getCemetery = (id: number) => invoke<CemeteryDTO>("get_cemetery", { id });
export const createCemetery = (req: CreateCemeteryRequest) => invoke<CemeteryDTO>("create_cemetery", { request: req });
export const updateCemetery = (id: number, req: UpdateCemeteryRequest) => invoke<CemeteryDTO>("update_cemetery", { id, request: req });
export const deleteCemetery = (id: number) => invoke<void>("delete_cemetery", { id });

// Plot
export const listPlots = (cemeteryId: number) => invoke<PlotDTO[]>("list_plots", { cemetery_id: cemeteryId });
export const getPlot = (id: number) => invoke<PlotDTO>("get_plot", { id });
export const createPlot = (req: CreatePlotRequest) => invoke<PlotDTO>("create_plot", { request: req });
export const updatePlot = (id: number, req: UpdatePlotRequest) => invoke<PlotDTO>("update_plot", { id, request: req });

// Concession
export const listConcessions = (cemeteryId?: number) => invoke<ConcessionDTO[]>("list_concessions", cemeteryId ? { cemetery_id: cemeteryId } : {});
export const getConcession = (id: number) => invoke<ConcessionDTO>("get_concession", { id });
export const createConcession = (req: CreateConcessionRequest) => invoke<ConcessionDTO>("create_concession", { request: req });
export const updateConcession = (id: number, req: UpdateConcessionRequest) => invoke<ConcessionDTO>("update_concession", { id, request: req });

// Individual
export const listIndividuals = () => invoke<IndividualDTO[]>("list_individuals");
export const getIndividual = (id: number) => invoke<IndividualDTO>("get_individual", { id });
export const createIndividual = (req: CreateIndividualRequest) => invoke<IndividualDTO>("create_individual", { request: req });
export const updateIndividual = (id: number, req: UpdateIndividualRequest) => invoke<IndividualDTO>("update_individual", { id, request: req });
export const searchIndividuals = (query: string) => invoke<IndividualDTO[]>("search_individuals", { query });

// Burial
export const createBurial = (req: CreateBurialRequest) => invoke<BurialDTO>("create_burial", { request: req });
