import { api, withQuery } from "../../api/client";
import type { ContractStatus } from "../../api/types";
import type { Option } from "../../components/forms";
import type { Page } from "../../components/Table";

export interface ContractRow {
  id: number;
  code: string;
  company: { id: number; name: string; nit?: string };
  kind: string;
  kind_label: string;
  start_date: string;
  end_date: string;
  duration_label: string;
  status: ContractStatus;
  status_label: string;
  days_left: number;
  responsible_name: string;
  has_summary: boolean;
}

export interface ContractPage extends Page<ContractRow> {
  statuses: { value: ContractStatus; label: string; total: number }[];
}

/** Lo que leyó la IA del PDF. Todos los campos pueden faltar: el documento manda. */
export interface AiSummary {
  summary?: string;
  alerts?: string[];
  service?: string;
  duration_text?: string;
  provider_name?: string;
  payment_terms?: string;
  termination?: string;
  data_protection?: string;
  provider_obligations?: string[];
  client_obligations?: string[];
  client_nit_text?: string;
}

export interface ComparisonRow {
  label: string;
  read: string | number | null;
  registered: string | number | null;
  missing: boolean;
  differs: boolean;
}

export interface ContractDetail extends ContractRow {
  company: { id: number; name: string; nit: string };
  /** El código tal como se registró (vacío si se muestra el automático CT-0000). */
  code_value: string;
  service: string;
  value: number | null;
  responsible_role: string;
  responsible_email: string;
  responsible_phone: string;
  notes: string;
  file_name: string;
  file_size: number;
  file_url: string;
  can_manage: boolean;
  ai_ready: boolean;
  // Solo para quien gestiona contratos:
  created_at?: string;
  created_by?: string | null;
  ai_summary?: AiSummary | null;
  ai_model?: string;
  ai_generated_at?: string | null;
  comparison?: ComparisonRow[];
  nit_mismatch?: boolean;
  history?: ContractRow[];
}

export interface ContractOptions {
  companies: { id: number; name: string }[];
  kinds: Option[];
  ai_ready: boolean;
}

export const CONTRACT_FIELDS = [
  "company", "code", "kind", "start_date", "end_date", "value", "service",
  "responsible_name", "responsible_role", "responsible_email", "responsible_phone", "notes",
] as const;

export type ContractField = (typeof CONTRACT_FIELDS)[number];
export type ContractValues = Record<ContractField, string>;

export interface Reading {
  fields: Partial<Record<ContractField, string | number | null>>;
  summary: string | null;
  client: string | null;
  client_nit: string | null;
  company_found: boolean;
  alerts: string[];
}

function formData(values: Partial<ContractValues>, document: File | null): FormData {
  const data = new FormData();
  for (const [name, value] of Object.entries(values)) data.append(name, value ?? "");
  if (document) data.append("document", document);
  return data;
}

export const contractsApi = {
  list: (params: { q: string; status: string; page: number }, signal: AbortSignal) =>
    api<ContractPage>(withQuery("/contracts/", params), { signal }),
  options: (signal: AbortSignal) => api<ContractOptions>("/contracts/options/", { signal }),
  get: (id: number, signal?: AbortSignal) => api<ContractDetail>(`/contracts/${id}/`, signal ? { signal } : {}),
  create: (values: ContractValues, document: File | null) =>
    api<{ id: number }>("/contracts/", { method: "POST", body: formData(values, document) }),
  update: (id: number, values: Omit<ContractValues, "company">, document: File | null) =>
    api<{ id: number }>(`/contracts/${id}/`, { method: "PUT", body: formData(values, document) }),
  remove: (id: number) => api<void>(`/contracts/${id}/`, { method: "DELETE" }),
  summarize: (id: number) => api<ContractDetail>(`/contracts/${id}/summary/`, { method: "POST" }),
  read: (document: File) => {
    const data = new FormData();
    data.append("document", document);
    return api<Reading>("/contracts/read/", { method: "POST", body: data });
  },
};

const money = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
export const formatMoney = (value: number) => `$ ${money.format(value)}`;

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace(".", ",")} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}
