import { api, withQuery } from "../../api/client";
import type { Option } from "../../components/forms";
import type { Page } from "../../components/Table";
import type { Account } from "../companies/api";

export type { Account };

export interface AccountPage extends Page<Account> {
  creatable_roles: Option[];
  role_filter: Option[];
  companies: { id: number; name: string }[];
}

export interface AccountInput {
  first_name: string;
  last_name: string;
  email: string;
  role?: string;
  company?: string;
  password1?: string;
  password2?: string;
}

export interface TemporaryPasswordInput {
  new_password1: string;
  new_password2: string;
}

export const accountsApi = {
  list: (params: { q: string; role: string; page: number }, signal: AbortSignal) =>
    api<AccountPage>(withQuery("/accounts/", params), { signal }),
  create: (input: AccountInput) => api<Account>("/accounts/", { method: "POST", body: input }),
  update: (id: number, input: AccountInput) => api<Account>(`/accounts/${id}/`, { method: "PUT", body: input }),
  setPassword: (id: number, input: TemporaryPasswordInput) =>
    api<Account>(`/accounts/${id}/password/`, { method: "POST", body: input }),
  setActive: (id: number, isActive: boolean) =>
    api<Account>(`/accounts/${id}/active/`, { method: "POST", body: { is_active: isActive } }),
};
