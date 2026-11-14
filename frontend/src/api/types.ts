/** Tipos de las respuestas de la API v1. Deben coincidir con apps/api/presenters.py. */

export type Role = "admin" | "ingeniero" | "empresa";

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  initials: string;
  role: Role;
  role_label: string;
  company: { id: number; name: string } | null;
  must_change_password: boolean;
  is_staff: boolean;
}

/** Entrada del menú: `to` es una ruta de React; `href`, una pantalla aún no migrada. */
export interface NavItem {
  label: string;
  icon: string;
  to: string | null;
  href: string | null;
}

export interface Session {
  user: User;
  capabilities: string[];
  navigation: NavItem[];
  admin_url: string | null;
}

export type Tone = "blue" | "amber" | "orange" | "teal" | "red" | "green" | "neutral";

export interface Level {
  key: string;
  label: string;
  tone: Tone;
}

export interface Visit {
  id: number;
  company: string;
  site: string;
  municipality: string;
  starts_at: string;
  ends_at: string;
  contact_name: string;
  status: "programada" | "realizada" | "cancelada";
  level: Level;
  url: string;
}

export type TrafficLight = "verde" | "amarillo" | "rojo";

export interface Risk {
  score: number;
  level: number;
  traffic_light: TrafficLight;
  label: string;
}

export interface Evaluation {
  id: number;
  code: string;
  company: string;
  area: string;
  position: string;
  evaluated_on: string;
  status: "borrador" | "terminada";
  status_label: string;
  risk: Risk | null;
  url: string;
}

export type ContractStatus = "por_iniciar" | "vigente" | "por_vencer" | "vencido";

export interface Contract {
  id: number;
  code: string;
  company: string;
  kind_label: string;
  start_date: string;
  end_date: string;
  status: ContractStatus;
  status_label: string;
  days_left: number;
  url: string;
}

interface DashboardBase {
  greeting: string;
  today: string;
  display_name: string;
}

export interface SupportDashboard extends DashboardBase {
  role: "admin";
  users_by_role: { role: Role; label: string; total: number }[];
  has_engineer: boolean;
  ai_ready: boolean;
  recent_accounts: (User & { is_active: boolean })[];
}

export interface EngineerDashboard extends DashboardBase {
  role: "ingeniero";
  totals: { companies: number; sites: number; areas: number; positions: number };
  contract_counts: Record<ContractStatus, number>;
  steps: { label: string; done: boolean }[];
  onboarding: boolean;
  to_close: Visit[];
  to_close_count: number;
  upcoming_visits: Visit[];
  without_evaluation: Visit[];
  expiring_contracts: Contract[];
  drafts_count: number;
  recent_evaluations: Evaluation[];
}

export interface CompanyDashboard extends DashboardBase {
  role: "empresa";
  company: { id: number; name: string } | null;
  counts: { sites: number; areas: number; positions: number; workers: number } | null;
  contract: Contract | null;
  pending_count: number;
  upcoming_visits: Visit[];
  recent_evaluations: Evaluation[];
}

/** Unión discriminada por `role`: TypeScript obliga a manejar cada panel. */
export type Dashboard = SupportDashboard | EngineerDashboard | CompanyDashboard;
