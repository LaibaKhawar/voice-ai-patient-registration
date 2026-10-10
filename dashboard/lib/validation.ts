/**
 * Light client-side validation mirroring backend app/validation.py.
 * The server remains authoritative; these checks only give faster feedback.
 */
import type { PatientField } from "./api";
import { STATE_CODES, SEX_OPTIONS } from "./constants";
import { digitsOnly } from "./format";

export type PatientFormValues = Record<PatientField, string>;

export const REQUIRED_FIELDS: PatientField[] = [
  "first_name",
  "last_name",
  "date_of_birth",
  "sex",
  "phone_number",
  "address_line_1",
  "city",
  "state",
  "zip_code",
];

export const ALL_FIELDS: PatientField[] = [
  ...REQUIRED_FIELDS,
  "email",
  "address_line_2",
  "insurance_provider",
  "insurance_member_id",
  "preferred_language",
  "emergency_contact_name",
  "emergency_contact_phone",
];

export function isRequired(field: PatientField) {
  return REQUIRED_FIELDS.includes(field);
}

const NAME_RE = /^[\p{L}]+(?:[ '\-][\p{L}]+)*'?$/u;
const PHONE_RE = /^[2-9]\d{2}[2-9]\d{6}$/;
const ZIP_RE = /^\d{5}(-?\d{4})?$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MEMBER_RE = /^[A-Z0-9]{1,30}$/;
const LANG_RE = /^[\p{L}]+(?:[ \-][\p{L}]+)*$/u;

export function normalizePhone(v: string) {
  let d = digitsOnly(v);
  if (d.length === 11 && d.startsWith("1")) d = d.slice(1);
  return d;
}

function phoneError(v: string) {
  const d = normalizePhone(v);
  if (d.length !== 10) return "Enter a 10-digit U.S. phone number.";
  if (!PHONE_RE.test(d)) return "Area code and exchange cannot start with 0 or 1.";
  return null;
}

function todayIso() {
  const t = new Date();
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
}

export { todayIso };

function check(field: PatientField, raw: string): string | null {
  const v = raw.trim();
  if (!v) return isRequired(field) ? "Required." : null;
  switch (field) {
    case "first_name":
    case "last_name":
      if (v.length > 50) return "Must be 50 characters or fewer.";
      return NAME_RE.test(v.replace(/\s+/g, " ").replace(/’/g, "'"))
        ? null
        : "Letters, spaces, hyphens and apostrophes only.";
    case "emergency_contact_name":
      if (v.length > 100) return "Must be 100 characters or fewer.";
      return NAME_RE.test(v.replace(/\s+/g, " ").replace(/’/g, "'"))
        ? null
        : "Letters, spaces, hyphens and apostrophes only.";
    case "date_of_birth": {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return "Enter a valid date.";
      if (v > todayIso()) return "Date of birth cannot be in the future.";
      if (v < "1900-01-01") return "Must be after the year 1900.";
      return null;
    }
    case "sex":
      return (SEX_OPTIONS as string[]).includes(v) ? null : "Select an option.";
    case "phone_number":
    case "emergency_contact_phone":
      return phoneError(v);
    case "email":
      return EMAIL_RE.test(v) ? null : "Enter a valid email address.";
    case "address_line_1":
    case "address_line_2":
      if (v.length > 100) return "Must be 100 characters or fewer.";
      return /[A-Za-z0-9]/.test(v) ? null : "Does not look like a street address.";
    case "city":
      if (v.length > 100) return "Must be 100 characters or fewer.";
      return /\p{L}/u.test(v) ? null : "Does not look like a city name.";
    case "state":
      return STATE_CODES.has(v.toUpperCase()) ? null : "Select a state.";
    case "zip_code":
      return ZIP_RE.test(v.replace(/\s/g, "")) ? null : "Enter a 5-digit ZIP or ZIP+4 (12345-6789).";
    case "insurance_provider":
      return v.length > 100 ? "Must be 100 characters or fewer." : null;
    case "insurance_member_id":
      return MEMBER_RE.test(v.replace(/[\s-]/g, "").toUpperCase())
        ? null
        : "Letters and numbers only, up to 30 characters.";
    case "preferred_language":
      return v.length <= 50 && LANG_RE.test(v) ? null : "Enter a language name, like English or Spanish.";
    default:
      return null;
  }
}

export function validatePatient(values: PatientFormValues): Partial<Record<PatientField, string>> {
  const errors: Partial<Record<PatientField, string>> = {};
  for (const f of ALL_FIELDS) {
    const msg = check(f, values[f] ?? "");
    if (msg) errors[f] = msg;
  }
  return errors;
}

/** Canonical form used both to compare edits and to build the request body. */
export function normalizeValue(field: PatientField, raw: string): string {
  const v = raw.trim().replace(/\s+/g, " ");
  if (!v) return "";
  switch (field) {
    case "phone_number":
    case "emergency_contact_phone":
      return normalizePhone(v);
    case "state":
      return v.toUpperCase();
    case "zip_code": {
      const z = v.replace(/\s/g, "");
      return /^\d{9}$/.test(z) ? `${z.slice(0, 5)}-${z.slice(5)}` : z;
    }
    case "email":
      return v.toLowerCase();
    case "insurance_member_id":
      return v.replace(/[\s-]/g, "").toUpperCase();
    default:
      return v;
  }
}
