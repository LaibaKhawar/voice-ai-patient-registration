"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight, Search, SearchX, UserPlus, Users, X } from "lucide-react";
import { api, type Patient, type PatientListParams, type PatientSort } from "@/lib/api";
import { PATIENT_PAGE_SIZE } from "@/lib/constants";
import {
  ageFromDob,
  formatCalendarDate,
  formatDateTime,
  formatNumber,
  formatPhone,
  listName,
  timeAgo,
} from "@/lib/format";
import { useDebouncedValue, useQuery } from "@/lib/hooks";
import { normalizePhone, todayIso } from "@/lib/validation";
import { PageHeader } from "@/components/page-header";
import { ErrorState } from "@/components/error-state";
import { Pagination } from "@/components/pagination";
import { Button, buttonClass } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

const SORTS: { value: string; label: string }[] = [
  { value: "created_at.desc", label: "Newest registrations" },
  { value: "created_at.asc", label: "Oldest registrations" },
  { value: "updated_at.desc", label: "Recently updated" },
  { value: "last_name.asc", label: "Last name, A–Z" },
  { value: "last_name.desc", label: "Last name, Z–A" },
  { value: "first_name.asc", label: "First name, A–Z" },
  { value: "date_of_birth.desc", label: "Youngest first" },
  { value: "date_of_birth.asc", label: "Oldest first" },
];
const DEFAULT_SORT = "created_at.desc";
const TEXT_KEYS = ["q", "last_name", "phone"] as const;
type TextKey = (typeof TEXT_KEYS)[number];
type Draft = Record<TextKey, string>;

function readDraft(params: URLSearchParams): Draft {
  return { q: params.get("q") ?? "", last_name: params.get("last_name") ?? "", phone: params.get("phone") ?? "" };
}

function toApiParams(params: URLSearchParams): PatientListParams {
  const sortValue = SORTS.some((s) => s.value === params.get("sort")) ? params.get("sort")! : DEFAULT_SORT;
  const [sort, order] = sortValue.split(".") as [PatientSort, "asc" | "desc"];
  const page = Math.max(1, Number.parseInt(params.get("page") ?? "1", 10) || 1);
  const phone = normalizePhone(params.get("phone") ?? "");
  return {
    q: params.get("q")?.trim() || undefined,
    last_name: params.get("last_name")?.trim() || undefined,
    date_of_birth: params.get("dob") || undefined,
    // Only send a phone filter once it is a full 10-digit number (the API rejects partials).
    phone_number: phone.length === 10 ? phone : undefined,
    sort,
    order,
    limit: PATIENT_PAGE_SIZE,
    offset: (page - 1) * PATIENT_PAGE_SIZE,
  };
}

export function PatientsView() {
  const router = useRouter();
  const params = useSearchParams();
  const paramsString = params.toString();

  const [draft, setDraft] = useState<Draft>(() => readDraft(params));
  const debounced = useDebouncedValue(draft, 300);
  const lastApplied = useRef(debounced);

  const replaceUrl = (next: URLSearchParams) => {
    const qs = next.toString();
    router.replace(qs ? `/patients/?${qs}` : "/patients/", { scroll: false });
  };

  // Push debounced text filters into the URL (resetting to page 1).
  useEffect(() => {
    if (lastApplied.current === debounced) return;
    lastApplied.current = debounced;
    const next = new URLSearchParams(paramsString);
    let changed = false;
    for (const k of TEXT_KEYS) {
      const v = debounced[k].trim();
      if ((next.get(k) ?? "") !== v) {
        if (v) next.set(k, v);
        else next.delete(k);
        changed = true;
      }
    }
    if (changed) {
      next.delete("page");
      const qs = next.toString();
      router.replace(qs ? `/patients/?${qs}` : "/patients/", { scroll: false });
    }
  }, [debounced, paramsString, router]);

  const apiParams = useMemo(() => toApiParams(new URLSearchParams(paramsString)), [paramsString]);
  const { data, error, loading, reload } = useQuery(`patients?${JSON.stringify(apiParams)}`, (signal) =>
    api.listPatients(apiParams, signal),
  );

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(paramsString);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    replaceUrl(next);
  };

  const hasFilters =
    TEXT_KEYS.some((k) => draft[k].trim() !== "") || !!params.get("dob");

  const clearFilters = () => {
    const empty = { q: "", last_name: "", phone: "" };
    setDraft(empty);
    const next = new URLSearchParams();
    const sort = params.get("sort");
    if (sort) next.set("sort", sort);
    replaceUrl(next);
  };

  const phoneDigits = normalizePhone(draft.phone);
  const phoneIncomplete = draft.phone.trim() !== "" && phoneDigits.length !== 10;
  const patients = data?.items ?? [];
  const total = data?.meta.total ?? 0;

  return (
    <>
      <PageHeader
        title="Patients"
        description={
          data ? `${formatNumber(total)} ${total === 1 ? "patient" : "patients"}${hasFilters ? " match" : ""}` : " "
        }
        actions={
          <Link href="/patients/new/" className={buttonClass("primary", "md")}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            New patient
          </Link>
        }
      />

      <Card>
        <div className="space-y-3 border-b border-zinc-200 p-3 sm:p-4">
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="relative flex-1">
              <label htmlFor="patient-search" className="sr-only">
                Search patients
              </label>
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
                aria-hidden="true"
              />
              <Input
                id="patient-search"
                type="search"
                placeholder="Search by name, email or phone"
                leadingIcon
                value={draft.q}
                onChange={(e) => setDraft((d) => ({ ...d, q: e.target.value }))}
                autoComplete="off"
              />
            </div>
            <div className="sm:w-56">
              <label htmlFor="patient-sort" className="sr-only">
                Sort by
              </label>
              <Select
                id="patient-sort"
                value={params.get("sort") && SORTS.some((s) => s.value === params.get("sort")) ? params.get("sort")! : DEFAULT_SORT}
                onChange={(e) => setParam("sort", e.target.value === DEFAULT_SORT ? "" : e.target.value)}
              >
                {SORTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    Sort: {s.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
            <div>
              <Label htmlFor="filter-last-name">
                Last name
              </Label>
              <Input
                id="filter-last-name"
                placeholder="Exact match"
                value={draft.last_name}
                onChange={(e) => setDraft((d) => ({ ...d, last_name: e.target.value }))}
                autoComplete="off"
              />
            </div>
            <div>
              <Label htmlFor="filter-dob">
                Date of birth
              </Label>
              <Input
                id="filter-dob"
                type="date"
                max={todayIso()}
                min="1900-01-01"
                value={params.get("dob") ?? ""}
                onChange={(e) => setParam("dob", e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="filter-phone">
                Phone
              </Label>
              <Input
                id="filter-phone"
                type="tel"
                inputMode="tel"
                placeholder="(512) 555-0142"
                value={draft.phone}
                onChange={(e) => setDraft((d) => ({ ...d, phone: e.target.value }))}
                aria-describedby={phoneIncomplete ? "filter-phone-hint" : undefined}
                autoComplete="off"
              />
            </div>
            <Button variant="ghost" onClick={clearFilters} disabled={!hasFilters} className="justify-self-start">
              <X className="h-4 w-4" aria-hidden="true" />
              Clear filters
            </Button>
          </div>
          {phoneIncomplete && (
            <p id="filter-phone-hint" className="text-xs text-zinc-500">
              Phone filter applies once all 10 digits are entered.
            </p>
          )}
        </div>

        <div aria-live="polite" aria-busy={loading}>
          {error ? (
            <ErrorState error={error} onRetry={reload} title="Couldn't load patients" />
          ) : loading && !data ? (
            <PatientsSkeleton />
          ) : patients.length === 0 ? (
            hasFilters ? (
              <EmptyState
                icon={SearchX}
                title="No patients match these filters"
                description="Try a different search, or clear the filters to see everyone."
                action={
                  <Button size="sm" onClick={clearFilters}>
                    Clear filters
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={Users}
                title="No patients yet"
                description="Patients registered through the voice agent appear here automatically. You can also add one manually."
                action={
                  <Link href="/patients/new/" className={buttonClass("primary", "sm")}>
                    <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
                    New patient
                  </Link>
                }
              />
            )
          ) : (
            <div className={loading ? "opacity-60 transition-opacity duration-150" : "transition-opacity duration-150"}>
              <PatientsTable patients={patients} onOpen={(id) => router.push(`/patients/view/?id=${id}`)} />
              <PatientCards patients={patients} />
            </div>
          )}
        </div>

        {data && !error && (
          <Pagination
            offset={apiParams.offset ?? 0}
            limit={PATIENT_PAGE_SIZE}
            total={total}
            noun={total === 1 ? "patient" : "patients"}
            onPage={(offset) => {
              setParam("page", offset === 0 ? "" : String(offset / PATIENT_PAGE_SIZE + 1));
              window.scrollTo({ top: 0 });
            }}
          />
        )}
      </Card>
    </>
  );
}

function DobCell({ dob }: { dob: string }) {
  const age = ageFromDob(dob);
  return (
    <span className="tabular-nums">
      {formatCalendarDate(dob)}
      {age !== null && <span className="ml-1.5 text-zinc-500">({age})</span>}
    </span>
  );
}

function PatientsTable({ patients, onOpen }: { patients: Patient[]; onOpen: (id: string) => void }) {
  return (
    <div className="hidden md:block">
      <Table>
        <THead>
          <tr>
            <TH>Name</TH>
            <TH>Date of birth</TH>
            <TH>Sex</TH>
            <TH>Phone</TH>
            <TH>City / State</TH>
            <TH>Registered</TH>
          </tr>
        </THead>
        <TBody>
          {patients.map((p) => (
            <TR
              key={p.patient_id}
              className="cursor-pointer transition-colors duration-150 hover:bg-zinc-50"
              onClick={(e) => {
                if ((e.target as HTMLElement).closest("a")) return;
                onOpen(p.patient_id);
              }}
            >
              <TD className="font-medium text-zinc-900">
                <Link
                  href={`/patients/view/?id=${p.patient_id}`}
                  className="rounded hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                >
                  {listName(p)}
                </Link>
              </TD>
              <TD>
                <DobCell dob={p.date_of_birth} />
              </TD>
              <TD>{p.sex}</TD>
              <TD className="tabular-nums">{formatPhone(p.phone_number)}</TD>
              <TD>
                {p.city}, {p.state}
              </TD>
              <TD>
                <time dateTime={p.created_at} title={formatDateTime(p.created_at)} className="tabular-nums text-zinc-500">
                  {timeAgo(p.created_at)}
                </time>
              </TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </div>
  );
}

function PatientCards({ patients }: { patients: Patient[] }) {
  return (
    <ul className="divide-y divide-zinc-200 md:hidden">
      {patients.map((p) => (
        <li key={p.patient_id}>
          <Link
            href={`/patients/view/?id=${p.patient_id}`}
            className="flex items-center gap-3 px-4 py-3 transition-colors duration-150 hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-3">
                <p className="truncate text-sm font-medium text-zinc-900">{listName(p)}</p>
                <time dateTime={p.created_at} title={formatDateTime(p.created_at)} className="shrink-0 text-xs text-zinc-500">
                  {timeAgo(p.created_at)}
                </time>
              </div>
              <p className="mt-0.5 text-[13px] text-zinc-600">
                <DobCell dob={p.date_of_birth} /> · {p.sex}
              </p>
              <p className="mt-0.5 truncate text-[13px] tabular-nums text-zinc-500">
                {formatPhone(p.phone_number)} · {p.city}, {p.state}
              </p>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-zinc-400" aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ul>
  );
}

function PatientsSkeleton() {
  return (
    <div aria-hidden="true">
      <div className="hidden md:block">
        <div className="h-9 border-b border-zinc-200 bg-zinc-50" />
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="grid h-11 grid-cols-6 items-center gap-4 border-b border-zinc-200 px-4 last:border-b-0">
            <Skeleton className="h-3.5 w-32" />
            <Skeleton className="h-3.5 w-28" />
            <Skeleton className="h-3.5 w-12" />
            <Skeleton className="h-3.5 w-28" />
            <Skeleton className="h-3.5 w-24" />
            <Skeleton className="h-3.5 w-16" />
          </div>
        ))}
      </div>
      <div className="divide-y divide-zinc-200 md:hidden">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="space-y-2 px-4 py-3.5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-48" />
            <Skeleton className="h-3 w-36" />
          </div>
        ))}
      </div>
    </div>
  );
}
