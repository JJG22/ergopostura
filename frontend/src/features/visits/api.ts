import { api, withQuery } from "../../api/client";
import type { Level } from "../../api/types";
import type { Option } from "../../components/forms";
import type { Page } from "../../components/Table";

export interface VisitRow {
  id: number;
  company: { id: number; name: string };
  site: string;
  municipality: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  contact_name: string;
  status: "programada" | "realizada" | "cancelada";
  level: Level;
  color: number;
}

export interface CalendarEvent {
  busy: boolean;
  starts_at: string;
  ends_at: string;
  top: number;
  height: number;
  left: number;
  width: number;
  // Solo en visitas que el usuario puede ver (no en «Ocupado»):
  id?: number;
  title?: string;
  company?: string;
  color?: number;
  level?: Level;
}

export interface CalendarDay {
  date: string;
  in_period: boolean;
  is_today: boolean;
  is_past: boolean;
  weekday: string;
  events: CalendarEvent[];
  open_hours: number[];
}

export interface ScheduleInfo {
  can_schedule: boolean;
  schedules: boolean;
  blocker: string;
  contract: { code: string; start_date: string; end_date: string } | null;
}

export type CalendarView = "mes" | "semana";

export interface Calendar extends ScheduleInfo {
  view: CalendarView;
  title: string;
  anchor: string;
  previous: string;
  next: string;
  today: string;
  contains_today: boolean;
  first_hour: number;
  last_hour: number;
  hour_height: number;
  grid_height: number;
  now_top: number | null;
  hours: string[];
  days: CalendarDay[];
  max_chips: number;
  shows_company: boolean;
  legend: { name: string; color: number }[];
  levels: Level[];
  upcoming: VisitRow[];
  to_close: VisitRow[];
}

export type AgendaTab = "proximas" | "por_cerrar" | "historial";

export interface AgendaPage extends Page<VisitRow>, ScheduleInfo {
  tab: AgendaTab;
  attends: boolean;
}

export interface VisitDetail extends VisitRow {
  site_id: number;
  address: string;
  duration_label: string;
  purpose: string;
  contact_phone: string;
  requested_by: string | null;
  created_at: string | null;
  completed_by: string | null;
  completed_at: string | null;
  completion_notes: string;
  cancelled_by: string | null;
  cancelled_at: string | null;
  cancellation_reason: string;
  evaluations: { id: number; code: string; url: string }[];
  can_reschedule: boolean;
  can_cancel: boolean;
  can_complete: boolean;
  can_evaluate: boolean;
  cancel_by_company: boolean;
  new_evaluation_url: string;
}

export interface VisitOptions extends ScheduleInfo {
  sites: Option[];
  durations: Option[];
  work_start: string;
  work_end: string;
}

export interface VisitInput {
  date: string;
  time: string;
  duration_minutes: string;
  site: string;
  purpose: string;
  contact_name: string;
  contact_phone: string;
}

export const visitsApi = {
  calendar: (params: { view: string; date: string }, signal: AbortSignal) =>
    api<Calendar>(withQuery("/visits/calendar/", params), { signal }),
  agenda: (params: { tab: string; page: number }, signal: AbortSignal) =>
    api<AgendaPage>(withQuery("/visits/agenda/", params), { signal }),
  get: (id: number, signal?: AbortSignal) => api<VisitDetail>(`/visits/${id}/`, signal ? { signal } : {}),
  options: (signal: AbortSignal) => api<VisitOptions>("/visits/options/", { signal }),
  create: (input: VisitInput) => api<VisitRow>("/visits/", { method: "POST", body: input }),
  reschedule: (id: number, input: VisitInput) => api<VisitRow>(`/visits/${id}/`, { method: "PUT", body: input }),
  complete: (id: number, notes: string) =>
    api<VisitDetail>(`/visits/${id}/complete/`, { method: "POST", body: { completion_notes: notes } }),
  cancel: (id: number, reason: string) =>
    api<VisitDetail>(`/visits/${id}/cancel/`, { method: "POST", body: { cancellation_reason: reason } }),
};

/** Mismos colores por empresa que el calendario actual (calendar.css, .c0 a .c7). */
export const PALETTE: readonly { fg: string; bg: string }[] = [
  { fg: "#0f766e", bg: "#ccfbf1" }, { fg: "#1d4ed8", bg: "#dbeafe" }, { fg: "#6d28d9", bg: "#ede9fe" },
  { fg: "#4338ca", bg: "#e0e7ff" }, { fg: "#0369a1", bg: "#e0f2fe" }, { fg: "#a21caf", bg: "#fae8ff" },
  { fg: "#0e7490", bg: "#cffafe" }, { fg: "#334155", bg: "#e2e8f0" },
];

export const colorOf = (index: number | undefined) => PALETTE[index ?? 7] ?? { fg: "#334155", bg: "#e2e8f0" };
