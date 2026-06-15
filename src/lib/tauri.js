import { invoke } from "@tauri-apps/api/core";
// Cemetery
export const listCemeteries = () => invoke("list_cemeteries");
export const getCemetery = (id) => invoke("get_cemetery", { id });
export const createCemetery = (req) => invoke("create_cemetery", { request: req });
export const updateCemetery = (id, req) => invoke("update_cemetery", { id, request: req });
export const deleteCemetery = (id) => invoke("delete_cemetery", { id });
// Plot
export const listPlots = (cemeteryId) => invoke("list_plots", { cemetery_id: cemeteryId });
export const getPlot = (id) => invoke("get_plot", { id });
export const createPlot = (req) => invoke("create_plot", { request: req });
export const updatePlot = (id, req) => invoke("update_plot", { id, request: req });
// Concession
export const listConcessions = (cemeteryId) => invoke("list_concessions", cemeteryId ? { cemetery_id: cemeteryId } : {});
export const getConcession = (id) => invoke("get_concession", { id });
export const createConcession = (req) => invoke("create_concession", { request: req });
export const updateConcession = (id, req) => invoke("update_concession", { id, request: req });
// Individual
export const listIndividuals = () => invoke("list_individuals");
export const getIndividual = (id) => invoke("get_individual", { id });
export const createIndividual = (req) => invoke("create_individual", { request: req });
export const updateIndividual = (id, req) => invoke("update_individual", { id, request: req });
export const searchIndividuals = (query) => invoke("search_individuals", { query });
// Burial
export const createBurial = (req) => invoke("create_burial", { request: req });
