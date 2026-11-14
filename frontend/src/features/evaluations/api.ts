import { api, withQuery } from "../../api/client";
import type { Evaluation, Risk } from "../../api/types";
import type { Option } from "../../components/forms";
import type { Page } from "../../components/Table";

export type EvaluationRow = Evaluation & { company_id: number };

export interface AiTraceRow {
  label: string;
  suggested: number | null;
  registered: number;
  changed: boolean;
}

export interface PostureResult {
  photo_id: number;
  grand_score: number;
  action_level: number;
  description: string;
  risk: Risk;
  partial_scores: Record<string, number>;
  method: string;
  ai_trace: { on_other_photo: boolean; frontal: boolean; rows: AiTraceRow[] } | null;
}

export interface Photo {
  id: number;
  url: string;
  width?: number;
  height?: number;
}

export interface Posture {
  id: number;
  name: string;
  side: "derecho" | "izquierdo";
  side_label: string;
  duration_value: number;
  duration_unit: string;
  duration_unit_label: string;
  photos: Photo[];
  result: PostureResult | null;
  recommendations: { id: number; text: string; attended: boolean }[];
}

export interface EvaluationDetail extends EvaluationRow {
  company_nit: string;
  site: string;
  evaluator: string;
  visit: { id: number; date: string };
  visit_id: number;
  area_id: number;
  position_id: number;
  worker: { id: number; full_name: string } | null;
  activity_description: string;
  worker_context: string;
  carries_load: boolean;
  load_weight_kg: number | null;
  repetitive_movements: boolean;
  repetition_notes: string;
  completed_at: string | null;
  postures: Posture[];
  can_edit: boolean;
  can_reopen: boolean;
  completion_problems: string[];
  posture_options: { sides: Option[]; units: Option[] };
}

export interface EvaluationOptions {
  visits: Option[];
  areas: Option[];
  positions: Option[];
  workers: Option[];
  area_hint: string;
  evaluated_on: string | null;
}

export interface EvaluationInput {
  visit: string;
  area: string;
  position: string;
  worker: string;
  evaluated_on: string;
  activity_description: string;
  worker_context: string;
  carries_load: boolean;
  load_weight_kg: string;
  repetitive_movements: boolean;
  repetition_notes: string;
}

export interface PostureInput {
  name: string;
  side: string;
  duration_value: string;
  duration_unit: string;
}

export interface FieldSpec {
  name: string;
  label: string;
  type: "number" | "checkbox" | "select";
  help: string;
  choices?: Option[];
}

export type AssessmentValues = Record<string, number | boolean | string | null>;

export interface AssessmentForm {
  evaluation_id: number;
  posture: { id: number; name: string; side: "derecho" | "izquierdo"; side_label: string };
  photos: Photo[];
  photo: number | null;
  groups: { title: string; fields: FieldSpec[] }[];
  values: AssessmentValues;
  has_result: boolean;
}

export interface AiSuggestion {
  photo: number | null;
  side: string;
  model: string;
  frontal: boolean;
  angles: Record<string, number | null>;
}

export const evaluationsApi = {
  list: (params: { q: string; page: number }, signal: AbortSignal) =>
    api<Page<EvaluationRow>>(withQuery("/evaluations/", params), { signal }),
  options: (params: { visit?: string; area?: string; position?: string; evaluation?: number }, signal?: AbortSignal) =>
    api<EvaluationOptions>(withQuery("/evaluations/options/", params), signal ? { signal } : {}),
  get: (id: number, signal?: AbortSignal) => api<EvaluationDetail>(`/evaluations/${id}/`, signal ? { signal } : {}),
  create: (input: EvaluationInput) => api<{ id: number }>("/evaluations/", { method: "POST", body: input }),
  update: (id: number, input: EvaluationInput) => api<{ id: number }>(`/evaluations/${id}/`, { method: "PUT", body: input }),
  complete: (id: number) => api<EvaluationDetail>(`/evaluations/${id}/complete/`, { method: "POST" }),
  reopen: (id: number) => api<EvaluationDetail>(`/evaluations/${id}/reopen/`, { method: "POST" }),
  addPosture: (id: number, input: PostureInput) => api<{ id: number }>(`/evaluations/${id}/postures/`, { method: "POST", body: input }),
  updatePosture: (id: number, input: PostureInput) => api<{ id: number }>(`/evaluations/postures/${id}/`, { method: "PUT", body: input }),
  deletePosture: (id: number) => api<void>(`/evaluations/postures/${id}/`, { method: "DELETE" }),
  uploadPhoto: (postureId: number, file: File) => {
    const data = new FormData();
    data.append("photo", file);
    return api<Photo>(`/evaluations/postures/${postureId}/photos/`, { method: "POST", body: data });
  },
  deletePhoto: (id: number) => api<void>(`/evaluations/photos/${id}/`, { method: "DELETE" }),
  assessment: (postureId: number, signal: AbortSignal) => api<AssessmentForm>(`/evaluations/postures/${postureId}/assessment/`, { signal }),
  saveAssessment: (postureId: number, values: { values: AssessmentValues; photo: number; ai_suggestion: AiSuggestion | null }) =>
    api<{ evaluation_id: number; result: PostureResult }>(`/evaluations/postures/${postureId}/assessment/`, { method: "PUT", body: { ...values.values, photo: values.photo, ai_suggestion: values.ai_suggestion } }),
  addRecommendation: (postureId: number, text: string) =>
    api<{ id: number }>(`/evaluations/postures/${postureId}/recommendations/`, { method: "POST", body: { text } }),
  deleteRecommendation: (id: number) => api<void>(`/evaluations/recommendations/${id}/`, { method: "DELETE" }),
};

const decimal = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });
export const formatNumber = (value: number) => decimal.format(value);
