import { api, withQuery } from "../../api/client";
import type { Contract, User } from "../../api/types";
import type { Option } from "../../components/forms";
import type { Page } from "../../components/Table";

export interface PlaceRef {
  id: number;
  name: string;
}

interface Located {
  municipality: PlaceRef;
  department: PlaceRef;
  location: string;
}

export interface CompanyRow extends Located {
  id: number;
  name: string;
  nit: string;
  is_active: boolean;
  site_count: number | null;
}

export interface Worker {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  initials: string;
  document_type: string;
  document_number: string;
  document_display: string;
  hired_on: string | null;
  is_active: boolean;
}

export interface Position {
  id: number;
  key: string;
  name: string;
  description: string;
  workers: Worker[];
}

export interface Area {
  id: number;
  key: string;
  name: string;
  description: string;
  positions: Position[];
}

export interface Site extends Located {
  id: number;
  key: string;
  name: string;
  address: string;
  areas: Area[];
}

export interface Account extends User {
  is_active: boolean;
  last_login: string | null;
}

export interface CompanyDetail extends CompanyRow {
  counts: { sites: number; areas: number; positions: number; workers: number };
  sites: Site[];
  shows_contract: boolean;
  contract: Contract | null;
  accounts: Account[] | null;
  permissions: { view_all: boolean; manage: boolean; manage_accounts: boolean; manage_contracts: boolean };
  document_types: Option[];
}

/** Respuesta al guardar un nivel de la estructura: a qué nodo del árbol volver. */
export interface Saved {
  id: number;
  key: string;
  company_id: number;
}

export interface CompanyInput {
  name: string;
  nit: string;
  department: string;
  municipality: string;
  is_active?: boolean;
}

export interface SiteInput {
  name: string;
  department: string;
  municipality: string;
  address: string;
}

export interface NamedInput {
  name: string;
  description: string;
}

export interface WorkerInput {
  first_name: string;
  last_name: string;
  document_type: string;
  document_number: string;
  hired_on: string | null;
  is_active?: boolean;
}

export type Level = "sites" | "areas" | "positions" | "workers";

/** Ruta del padre (para crear) y del registro (para editar), por nivel. */
const PATHS: Record<Level, { parent: string; self: string }> = {
  sites: { parent: "companies", self: "sites" },
  areas: { parent: "sites", self: "areas" },
  positions: { parent: "areas", self: "positions" },
  workers: { parent: "positions", self: "workers" },
};

export const companiesApi = {
  list: (params: { q: string; page: number }, signal: AbortSignal) =>
    api<Page<CompanyRow>>(withQuery("/companies/", params), { signal }),
  get: (id: number, signal: AbortSignal) => api<CompanyDetail>(`/companies/${id}/`, { signal }),
  create: (input: CompanyInput) => api<{ id: number }>("/companies/", { method: "POST", body: input }),
  update: (id: number, input: CompanyInput) => api<{ id: number }>(`/companies/${id}/`, { method: "PUT", body: input }),
  createChild: (level: Level, parentId: number, input: object) =>
    api<Saved>(`/${PATHS[level].parent}/${parentId}/${level}/`, { method: "POST", body: input }),
  updateChild: (level: Level, id: number, input: object) =>
    api<Saved>(`/${PATHS[level].self}/${id}/`, { method: "PUT", body: input }),
};
