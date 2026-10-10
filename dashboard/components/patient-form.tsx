"use client";

import { useRef, useState } from "react";
import { CircleAlert } from "lucide-react";
import { api, ApiError, type Patient, type PatientCreate, type PatientField, type PatientUpdate } from "@/lib/api";
import { SEX_OPTIONS, US_STATES } from "@/lib/constants";
import { formatPhone } from "@/lib/format";
import {
  ALL_FIELDS,
  isRequired,
  normalizeValue,
  todayIso,
  validatePatient,
  type PatientFormValues,
} from "@/lib/validation";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select } from "./ui/select";

type Errors = Partial<Record<PatientField, string>>;

const LABELS: Record<PatientField, string> = {
  first_name: "First name",
  last_name: "Last name",
  date_of_birth: "Date of birth",
  sex: "Sex",
  phone_number: "Phone number",
  email: "Email",
  address_line_1: "Street address",
  address_line_2: "Apartment, suite or unit",
  city: "City",
  state: "State",
  zip_code: "ZIP code",
  insurance_provider: "Insurance provider",
  insurance_member_id: "Member ID",
  preferred_language: "Preferred language",
  emergency_contact_name: "Contact name",
  emergency_contact_phone: "Contact phone",
};

function toValues(p?: Patient): PatientFormValues {
  const v = {} as PatientFormValues;
  for (const f of ALL_FIELDS) {
    const raw = p ? p[f] : null;
    v[f] = raw ?? "";
  }
  if (p) {
    v.phone_number = formatPhone(p.phone_number);
    v.emergency_contact_phone = p.emergency_contact_phone ? formatPhone(p.emergency_contact_phone) : "";
  } else {
    v.preferred_language = "English";
  }
  return v;
}

function buildCreate(values: PatientFormValues): PatientCreate {
  const body: Record<string, string> = {};
  for (const f of ALL_FIELDS) {
    const v = normalizeValue(f, values[f]);
    if (v) body[f] = v;
  }
  return body as unknown as PatientCreate;
}

/** PUT is partial: send only changed fields; send null for optional fields the user cleared. */
function buildUpdate(values: PatientFormValues, initial: PatientFormValues): PatientUpdate {
  const body: PatientUpdate = {};
  for (const f of ALL_FIELDS) {
    const next = normalizeValue(f, values[f]);
    const prev = normalizeValue(f, initial[f]);
    if (next === prev) continue;
    body[f] = next === "" && !isRequired(f) ? null : next;
  }
  return body;
}

export function PatientForm({
  patient,
  onSaved,
  onCancel,
}: {
  patient?: Patient;
  onSaved: (p: Patient, changed: boolean) => void;
  onCancel: () => void;
}) {
  const isEdit = !!patient;
  const initial = useRef(toValues(patient));
  const [values, setValues] = useState<PatientFormValues>(initial.current);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const submitting = useRef(false);
  const formRef = useRef<HTMLFormElement>(null);
  // Stable idempotency key for this create attempt, so a retried submit can't duplicate.
  const idemKey = useRef<string>(
    typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : String(Date.now()),
  );

  const set = (f: PatientField) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const v = e.target.value;
    setValues((s) => ({ ...s, [f]: v }));
    if (errors[f]) setErrors((s) => ({ ...s, [f]: undefined }));
  };

  const focusFirstError = (errs: Errors) => {
    const first = ALL_FIELDS.find((f) => errs[f]);
    if (first) {
      requestAnimationFrame(() => {
        const el = formRef.current?.querySelector<HTMLElement>(`[name="${first}"]`);
        el?.focus();
      });
    }
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting.current) return;
    setFormError(null);

    const clientErrors = validatePatient(values);
    if (Object.keys(clientErrors).length > 0) {
      setErrors(clientErrors);
      setFormError("Please correct the highlighted fields.");
      focusFirstError(clientErrors);
      return;
    }

    let body: PatientCreate | PatientUpdate;
    if (isEdit) {
      body = buildUpdate(values, initial.current);
      if (Object.keys(body).length === 0) {
        onSaved(patient, false);
        return;
      }
    } else {
      body = buildCreate(values);
    }

    submitting.current = true;
    setPending(true);
    try {
      const saved = isEdit
        ? await api.updatePatient(patient.patient_id, body as PatientUpdate)
        : await api.createPatient(body as PatientCreate, idemKey.current);
      onSaved(saved, true);
    } catch (err) {
      submitting.current = false;
      setPending(false);
      if (err instanceof ApiError && err.details.length > 0) {
        const serverErrors: Errors = {};
        const unmatched: string[] = [];
        for (const d of err.details) {
          if ((ALL_FIELDS as string[]).includes(d.field)) {
            const f = d.field as PatientField;
            serverErrors[f] ??= capitalize(d.message);
          } else {
            unmatched.push(d.message);
          }
        }
        setErrors(serverErrors);
        setFormError(unmatched.length ? capitalize(unmatched.join(" ")) : "Please correct the highlighted fields.");
        focusFirstError(serverErrors);
      } else {
        setFormError(err instanceof ApiError ? err.message : "Could not save the patient. Please try again.");
      }
    }
  }

  const field = (f: PatientField, props: Omit<React.InputHTMLAttributes<HTMLInputElement>, "name"> = {}) => (
    <Field name={f} error={errors[f]}>
      <Input
        id={`f-${f}`}
        name={f}
        value={values[f]}
        onChange={set(f)}
        invalid={!!errors[f]}
        aria-describedby={errors[f] ? `f-${f}-error` : undefined}
        aria-required={isRequired(f) || undefined}
        {...props}
      />
    </Field>
  );

  return (
    <form ref={formRef} onSubmit={onSubmit} noValidate className="space-y-6">
      {formError && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>{formError}</p>
        </div>
      )}

      <Section title="Identity" description="Legal name, date of birth and sex as they appear on ID.">
        <div className="grid gap-4 sm:grid-cols-2">
          {field("first_name", { autoComplete: "given-name", maxLength: 50 })}
          {field("last_name", { autoComplete: "family-name", maxLength: 50 })}
          {field("date_of_birth", { type: "date", max: todayIso(), min: "1900-01-01", autoComplete: "bday" })}
          <Field name="sex" error={errors.sex}>
            <Select
              id="f-sex"
              name="sex"
              value={values.sex}
              onChange={set("sex")}
              invalid={!!errors.sex}
              aria-describedby={errors.sex ? "f-sex-error" : undefined}
              aria-required="true"
            >
              <option value="">Select…</option>
              {SEX_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Section>

      <Section title="Contact">
        <div className="grid gap-4 sm:grid-cols-2">
          {field("phone_number", { type: "tel", inputMode: "tel", autoComplete: "tel-national", placeholder: "(512) 555-0142" })}
          {field("email", { type: "email", autoComplete: "email", placeholder: "name@example.com" })}
        </div>
      </Section>

      <Section title="Address">
        <div className="grid gap-4 sm:grid-cols-4">
          <div className="sm:col-span-4">{field("address_line_1", { autoComplete: "address-line1", maxLength: 100 })}</div>
          <div className="sm:col-span-4">{field("address_line_2", { autoComplete: "address-line2", maxLength: 100 })}</div>
          <div className="sm:col-span-2">{field("city", { autoComplete: "address-level2", maxLength: 100 })}</div>
          <div className="sm:col-span-1">
            <Field name="state" error={errors.state}>
              <Select
                id="f-state"
                name="state"
                value={values.state}
                onChange={set("state")}
                invalid={!!errors.state}
                aria-describedby={errors.state ? "f-state-error" : undefined}
                aria-required="true"
                autoComplete="address-level1"
              >
                <option value="">Select…</option>
                {US_STATES.map(([code, name]) => (
                  <option key={code} value={code}>
                    {name} ({code})
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="sm:col-span-1">
            {field("zip_code", { inputMode: "numeric", autoComplete: "postal-code", maxLength: 10, placeholder: "78701" })}
          </div>
        </div>
      </Section>

      <Section title="Insurance" description="Optional. Leave blank for self-pay patients.">
        <div className="grid gap-4 sm:grid-cols-2">
          {field("insurance_provider", { maxLength: 100 })}
          {field("insurance_member_id", { maxLength: 30, autoCapitalize: "characters" })}
        </div>
      </Section>

      <Section title="Emergency contact" description="Optional.">
        <div className="grid gap-4 sm:grid-cols-2">
          {field("emergency_contact_name", { maxLength: 100 })}
          {field("emergency_contact_phone", { type: "tel", inputMode: "tel", placeholder: "(512) 555-0199" })}
        </div>
      </Section>

      <Section title="Preferences">
        <div className="grid gap-4 sm:grid-cols-2">
          {field("preferred_language", { maxLength: 50, placeholder: "English" })}
        </div>
      </Section>

      <div className="sticky bottom-0 -mx-4 flex flex-col-reverse gap-2 border-t border-zinc-200 bg-zinc-50/95 px-4 py-3 sm:static sm:mx-0 sm:flex-row sm:justify-end sm:border-0 sm:bg-transparent sm:px-0 sm:py-0">
        <Button variant="secondary" onClick={onCancel} disabled={pending}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={pending}>
          {pending ? "Saving…" : isEdit ? "Save changes" : "Create patient"}
        </Button>
      </div>
    </form>
  );
}

function capitalize(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  const id = `section-${title.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <section aria-labelledby={id} className="rounded-md border border-zinc-200 bg-white">
      <div className="border-b border-zinc-200 px-4 py-3">
        <h2 id={id} className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          {title}
        </h2>
        {description && <p className="mt-0.5 text-[13px] text-zinc-500">{description}</p>}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function Field({ name, error, children }: { name: PatientField; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <Label htmlFor={`f-${name}`} required={isRequired(name)}>
        {LABELS[name]}
      </Label>
      {children}
      <p
        id={`f-${name}-error`}
        className={cn("mt-1.5 text-[13px] text-rose-700", !error && "hidden")}
        aria-live="polite"
      >
        {error}
      </p>
    </div>
  );
}
