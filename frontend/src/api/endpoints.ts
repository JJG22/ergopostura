import { api } from "./client";
import type { Dashboard, Session } from "./types";

export interface LoginInput {
  email: string;
  password: string;
  remember: boolean;
}

export interface PasswordInput {
  old_password: string;
  new_password1: string;
  new_password2: string;
}

export const authApi = {
  session: (signal?: AbortSignal) => api<Session>("/auth/session/", signal ? { signal } : {}),
  login: (input: LoginInput) => api<Session>("/auth/login/", { method: "POST", body: input }),
  logout: () => api<void>("/auth/logout/", { method: "POST" }),
  changePassword: (input: PasswordInput) => api<Session>("/auth/password/", { method: "POST", body: input }),
};

export const dashboardApi = {
  get: (signal?: AbortSignal) => api<Dashboard>("/dashboard/", signal ? { signal } : {}),
};
