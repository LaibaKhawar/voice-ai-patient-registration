/**
 * Typed client for the FastAPI backend.
 *
 * Production: the dashboard is served by the backend at /dashboard, so requests go
 * to the same origin with relative URLs (`/patients`, not `/dashboard/patients`).
 * Development: set NEXT_PUBLIC_API_BASE=http://localhost:8000 and run the backend
 * with CORS_ORIGINS=http://localhost:3000.
 */

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/+$/, "");
export const BASE_PATH = "/dashboard";

// ---------- Types ----------

export type Sex = "Male" | "Female" | "Other" | "Decline to Answer";

export interface Patient {
  patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: Sex;
  phone_number: string;
  email: string | null;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  zip_code: string;
  insurance_provider: string | null;
  insurance_member_id: string | null;
  preferred_language: string;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export type PatientField = Exclude<
  keyof Patient,
  "patient_id" | "created_at" | "updated_at" | "deleted_at"
>;

export type PatientCreate = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: Sex;
  phone_number: string;
  address_line_1: string;
  city: string;
  state: string;
  zip_code: string;
  email?: string | null;
  address_line_2?: string | null;
  insurance_provider?: string | null;
  insurance_member_id?: string | null;
  preferred_language?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
};

export type PatientUpdate = Partial<{ [K in PatientField]: string | null }>;

export type CallOutcome = "registered" | "updated" | "failed" | "abandoned" | "no_registration";

export interface Call {
  id: string;
  vapi_call_id: string;
  caller_number: string | null;
  state: string;
  mode: "create" | "update" | string;
  outcome: CallOutcome | string | null;
  patient_id: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  ended_reason: string | null;
  summary: string | null;
  has_transcript: boolean;
  created_at: string;
}

export interface CallDetail extends Call {
  transcript: string | null;
  last_error: string | null;
}

export interface Stats {
  total_patients: number;
  registered_today: number;
  registrations_by_day: { date: string; count: number }[];
  total_calls: number;
  calls_by_outcome: Record<string, number>;
  generated_at: string;
}

export interface ListMeta {
  total: number;
  limit: number;
  offset: number;
}

export interface Paged<T> {
  items: T[];
  meta: ListMeta;
}

export interface FieldError {
  field: string;
  message: string;
}

interface Envelope<T> {
  data: T | null;
  error: { code: string; message: string; details?: FieldError[] } | null;
  meta?: ListMeta;
}

// ---------- Errors ----------

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: FieldError[];

  constructor(status: number, code: string, message: string, details: FieldError[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get isNotFound() {
    return this.status === 404 || this.code === "INVALID_ID";
  }

  /** Field-level messages keyed by field name (from 422 validation errors). */
  fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const d of this.details) {
      if (d.field && !(d.field in out)) out[d.field] = d.message;
    }
    return out;
  }
}

// ---------- Core request ----------

type Query = Record<string, string | number | undefined | null>;

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  query?: Query;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** Redirect to the login page on 401 (default true). */
  redirectOn401?: boolean;
}

let redirecting = false;

export function redirectToLogin(withNext = true) {
  if (typeof window === "undefined" || redirecting) return;
  const loginPath = `${BASE_PATH}/login/`;
  if (window.location.pathname.startsWith(loginPath)) return;
  redirecting = true;
  const here = window.location.pathname.slice(BASE_PATH.length) + window.location.search;
  const next = withNext && here && here !== "/" ? `?next=${encodeURIComponent(here)}` : "";
  window.location.assign(`${loginPath}${next}`);
}

function buildUrl(path: string, query?: Query) {
  const params = new URLSearchParams();
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
    }
  }
  const qs = params.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<{ data: T; meta?: ListMeta }> {
  const { method = "GET", body, query, headers, signal, redirectOn401 = true } = opts;
  let res: Response;
  try {
    res = await fetch(buildUrl(path, query), {
      method,
      signal,
      credentials: API_BASE ? "include" : "same-origin",
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "NETWORK_ERROR", "Could not reach the server. Check your connection and try again.");
  }

  let payload: Envelope<T> | null = null;
  try {
    payload = (await res.json()) as Envelope<T>;
  } catch {
    payload = null;
  }

  if (res.status === 401) {
    if (redirectOn401) redirectToLogin();
    throw new ApiError(401, payload?.error?.code ?? "UNAUTHORIZED", payload?.error?.message ?? "Not signed in.");
  }

  if (!res.ok || !payload || payload.error) {
    const e = payload?.error;
    throw new ApiError(
      res.status,
      e?.code ?? "HTTP_ERROR",
      e?.message ?? `Request failed (${res.status}).`,
      e?.details ?? [],
    );
  }

  return { data: payload.data as T, meta: payload.meta };
}

async function list<T>(path: string, query: Query, signal?: AbortSignal): Promise<Paged<T>> {
  const { data, meta } = await request<T[]>(path, { query, signal });
  return {
    items: data ?? [],
    meta: meta ?? { total: data?.length ?? 0, limit: data?.length ?? 0, offset: 0 },
  };
}

// ---------- Endpoints ----------

export type PatientSort = "created_at" | "updated_at" | "last_name" | "first_name" | "date_of_birth";

export interface PatientListParams {
  q?: string;
  last_name?: string;
  date_of_birth?: string;
  phone_number?: string;
  sort?: PatientSort;
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export const api = {
  login: (apiKey: string) =>
    request<{ authenticated: boolean }>("/auth/login", {
      method: "POST",
      body: { api_key: apiKey },
      redirectOn401: false,
    }).then((r) => r.data),
  logout: () =>
    request<{ authenticated: boolean }>("/auth/logout", { method: "POST", redirectOn401: false }).then(
      (r) => r.data,
    ),
  session: (signal?: AbortSignal) =>
    request<{ authenticated: boolean }>("/auth/session", { signal }).then((r) => r.data),
  ready: (signal?: AbortSignal) =>
    request<{ status: string; database: string }>("/ready", { signal, redirectOn401: false }).then(
      (r) => r.data,
    ),

  stats: (signal?: AbortSignal) => request<Stats>("/stats", { signal }).then((r) => r.data),

  listPatients: (params: PatientListParams, signal?: AbortSignal) =>
    list<Patient>("/patients", { ...params }, signal),
  getPatient: (id: string, signal?: AbortSignal) =>
    request<Patient>(`/patients/${encodeURIComponent(id)}`, { signal }).then((r) => r.data),
  /** `idempotencyKey` makes a retried submit return the same record instead of a duplicate. */
  createPatient: (body: PatientCreate, idempotencyKey?: string) =>
    request<Patient>("/patients", {
      method: "POST",
      body,
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
    }).then((r) => r.data),
  updatePatient: (id: string, body: PatientUpdate) =>
    request<Patient>(`/patients/${encodeURIComponent(id)}`, { method: "PUT", body }).then((r) => r.data),
  deletePatient: (id: string) =>
    request<Patient>(`/patients/${encodeURIComponent(id)}`, { method: "DELETE" }).then((r) => r.data),
  patientCalls: (id: string, signal?: AbortSignal) =>
    request<Call[]>(`/patients/${encodeURIComponent(id)}/calls`, { signal }).then((r) => r.data ?? []),

  listCalls: (params: { limit?: number; offset?: number }, signal?: AbortSignal) =>
    list<Call>("/calls", { ...params }, signal),
  getCall: (id: string, signal?: AbortSignal) =>
    request<CallDetail>(`/calls/${encodeURIComponent(id)}`, { signal }).then((r) => r.data),
};
