/**
 * Cliente HTTP de la API. Todo error llega como ApiError, con un código estable que el resto
 * de la aplicación usa para decidir qué hacer (volver al login, pedir cambio de contraseña,
 * marcar campos del formulario o mostrar un mensaje).
 */

export type ApiErrorCode =
  | "not_authenticated"
  | "invalid_credentials"
  | "password_change_required"
  | "permission_denied"
  | "not_found"
  | "validation_error"
  | "conflict"
  | "ai_unavailable"
  | "ai_failed"
  | "throttled"
  | "csrf_failed"
  | "network_error"
  | "server_error";

export type FieldErrors = Readonly<Record<string, readonly string[]>>;

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly fields: FieldErrors;

  constructor(code: ApiErrorCode, message: string, status: number, fields: FieldErrors = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.fields = fields;
  }

  /** Primer mensaje de un campo, para mostrarlo debajo de su entrada. */
  field(name: string): string | undefined {
    return this.fields[name]?.[0];
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** Convierte cualquier error en un ApiError, para que la interfaz maneje un solo tipo. */
export function toApiError(value: unknown): ApiError {
  if (isApiError(value)) return value;
  return new ApiError("server_error", "Ocurrió un error inesperado. Intenta de nuevo.", 0);
}

const KNOWN_CODES: ReadonlySet<string> = new Set<ApiErrorCode>([
  "not_authenticated", "invalid_credentials", "password_change_required", "permission_denied",
  "not_found", "validation_error", "conflict", "ai_unavailable", "ai_failed", "throttled", "csrf_failed", "network_error", "server_error",
]);

type ErrorListener = (error: ApiError) => void;
const listeners = new Set<ErrorListener>();

/** Permite reaccionar en un solo lugar a errores globales, como la sesión vencida. */
export function onApiError(listener: ErrorListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const BASE = "/api/v1";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name: string): string | undefined {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : undefined;
}

let csrfReady: Promise<void> | null = null;

async function ensureCsrf(): Promise<string> {
  if (!readCookie("csrftoken")) {
    csrfReady ??= fetch(`${BASE}/auth/csrf/`, { credentials: "same-origin" }).then(() => undefined);
    await csrfReady;
    csrfReady = null;
  }
  return readCookie("csrftoken") ?? "";
}

interface ErrorPayload {
  error?: { code?: string; message?: string; fields?: Record<string, string[]> };
  detail?: string;
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ErrorPayload = {};
  try {
    payload = (await response.json()) as ErrorPayload;
  } catch {
    // Una página de error HTML (por ejemplo, del proxy) no trae JSON.
  }
  const body = payload.error;
  if (response.status === 403 && !body && /csrf/i.test(payload.detail ?? "")) {
    return new ApiError("csrf_failed", "La sesión de seguridad venció. Recarga la página.", 403);
  }
  if (body?.code && KNOWN_CODES.has(body.code)) {
    return new ApiError(body.code as ApiErrorCode, body.message ?? "Ocurrió un error.", response.status, body.fields ?? {});
  }
  if (response.status === 401) return new ApiError("not_authenticated", "Tu sesión terminó. Ingresa de nuevo.", 401);
  if (response.status === 403) return new ApiError("permission_denied", body?.message ?? "No tienes permiso para hacer esto.", 403);
  if (response.status === 404) return new ApiError("not_found", "No encontramos lo que buscas.", 404);
  return new ApiError("server_error", "El servidor no pudo responder. Intenta de nuevo en un momento.", response.status);
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  // Un FormData (archivos) lo codifica el navegador con su propio límite multipart.
  const isForm = options.body instanceof FormData;
  if (options.body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (UNSAFE.has(method)) headers["X-CSRFToken"] = await ensureCsrf();

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      credentials: "same-origin",
      body: options.body === undefined ? null : isForm ? (options.body as FormData) : JSON.stringify(options.body),
      signal: options.signal ?? null,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    const error = new ApiError("network_error", "No hay conexión con el servidor. Revisa tu internet.", 0);
    listeners.forEach((listener) => listener(error));
    throw error;
  }

  if (!response.ok) {
    const error = await parseError(response);
    listeners.forEach((listener) => listener(error));
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Agrega parámetros de búsqueda a una ruta, omitiendo los vacíos. */
export function withQuery(path: string, params: Record<string, string | number | undefined | null>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}
