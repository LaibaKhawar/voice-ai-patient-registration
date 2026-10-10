"use client";

import Link from "next/link";
import { ArrowRight, PhoneCall, UserPlus, Users } from "lucide-react";
import { api, type Call, type Paged, type Patient, type Stats } from "@/lib/api";
import { SUCCESS_OUTCOMES, TERMINAL_OUTCOMES } from "@/lib/constants";
import { formatDateTime, formatDuration, formatNumber, listName, maskPhone, timeAgo } from "@/lib/format";
import { useQuery, type QueryState } from "@/lib/hooks";
import { PageHeader } from "@/components/page-header";
import { ErrorState } from "@/components/error-state";
import { OutcomeBadge } from "@/components/outcome-badge";
import { RegistrationsChart } from "@/components/registrations-chart";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonClass } from "@/components/ui/button";

function successRate(stats: Stats): { value: string; detail: string } {
  const by = stats.calls_by_outcome;
  const ended = TERMINAL_OUTCOMES.reduce((s, k) => s + (by[k] ?? 0), 0);
  const ok = SUCCESS_OUTCOMES.reduce((s, k) => s + (by[k] ?? 0), 0);
  if (ended === 0) return { value: "—", detail: "No completed calls yet" };
  return {
    value: `${Math.round((ok / ended) * 100)}%`,
    detail: `${formatNumber(ok)} of ${formatNumber(ended)} completed calls`,
  };
}

export function OverviewView() {
  const stats = useQuery("stats", (s) => api.stats(s));
  const patients = useQuery("recent-patients", (s) =>
    api.listPatients({ sort: "created_at", order: "desc", limit: 5 }, s),
  );
  const calls = useQuery("recent-calls", (s) => api.listCalls({ limit: 5 }, s));

  return (
    <>
      <PageHeader
        title="Overview"
        description="Registrations captured by the voice intake agent and staff."
        actions={
          <Link href="/patients/new/" className={buttonClass("primary", "md")}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            New patient
          </Link>
        }
      />

      <StatTiles stats={stats.data} loading={stats.loading} />
      {stats.error && (
        <Card className="mb-6">
          <ErrorState error={stats.error} onRetry={stats.reload} title="Couldn't load statistics" />
        </Card>
      )}

      <Card className="mb-6">
        <CardHeader
          title="Registrations, last 14 days"
          description={
            stats.data
              ? (() => {
                  const n = stats.data.registrations_by_day.reduce((s, d) => s + d.count, 0);
                  return `${formatNumber(n)} new ${n === 1 ? "patient" : "patients"} in this period`;
                })()
              : undefined
          }
        />
        <CardBody>
          {stats.loading && !stats.data ? (
            <Skeleton className="h-52 w-full" />
          ) : stats.data ? (
            <RegistrationsChart data={stats.data.registrations_by_day} />
          ) : (
            <p className="py-10 text-center text-[13px] text-zinc-500">Chart unavailable.</p>
          )}
        </CardBody>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentPatients state={patients} />
        <RecentCalls state={calls} />
      </div>
    </>
  );
}

function StatTiles({ stats, loading }: { stats: Stats | undefined; loading: boolean }) {
  const rate = stats ? successRate(stats) : null;
  const tiles = [
    { label: "Total patients", value: stats ? formatNumber(stats.total_patients) : null, detail: "Active records" },
    {
      label: "Registered today",
      value: stats ? formatNumber(stats.registered_today) : null,
      detail: "Since 00:00 UTC",
    },
    { label: "Calls handled", value: stats ? formatNumber(stats.total_calls) : null, detail: "All time" },
    { label: "Registration success", value: rate?.value ?? null, detail: rate?.detail ?? "Registered or updated" },
  ];
  return (
    <section aria-label="Key metrics" className="mb-6 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-zinc-200 bg-zinc-200 lg:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.label} className="bg-white px-4 py-3.5">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{t.label}</p>
          {loading && !stats ? (
            <Skeleton className="mt-2 h-7 w-16" />
          ) : (
            <p className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-zinc-900">{t.value ?? "—"}</p>
          )}
          <p className="mt-0.5 truncate text-xs text-zinc-500">{stats ? t.detail : " "}</p>
        </div>
      ))}
    </section>
  );
}

function ListSkeleton() {
  return (
    <ul aria-hidden="true" className="divide-y divide-zinc-100">
      {Array.from({ length: 5 }).map((_, i) => (
        <li key={i} className="flex h-14 items-center justify-between px-4">
          <div className="space-y-1.5">
            <Skeleton className="h-3.5 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
          <Skeleton className="h-3 w-14" />
        </li>
      ))}
    </ul>
  );
}

type ListState<T> = QueryState<Paged<T>>;

function ViewAll({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1 rounded text-[13px] font-medium text-teal-700 transition-colors duration-150 hover:text-teal-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
    >
      {label}
      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
    </Link>
  );
}

function RecentPatients({ state }: { state: ListState<Patient> }) {
  const items = state.data?.items ?? [];
  return (
    <Card>
      <CardHeader title="Recent registrations" action={<ViewAll href="/patients/" label="All patients" />} />
      {state.loading && !state.data ? (
        <ListSkeleton />
      ) : state.error ? (
        <ErrorState error={state.error} onRetry={state.reload} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No patients yet"
          description="Patients registered by phone or added here will appear in this list."
        />
      ) : (
        <ul className="divide-y divide-zinc-100">
          {items.map((p) => (
            <li key={p.patient_id}>
              <Link
                href={`/patients/view/?id=${p.patient_id}`}
                className="flex h-14 items-center justify-between gap-4 px-4 transition-colors duration-150 hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-zinc-900">{listName(p)}</p>
                  <p className="truncate text-xs text-zinc-500">
                    {p.city}, {p.state}
                  </p>
                </div>
                <time
                  dateTime={p.created_at}
                  title={formatDateTime(p.created_at)}
                  className="shrink-0 text-xs tabular-nums text-zinc-500"
                >
                  {timeAgo(p.created_at)}
                </time>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function RecentCalls({ state }: { state: ListState<Call> }) {
  const items = state.data?.items ?? [];
  return (
    <Card>
      <CardHeader title="Recent calls" action={<ViewAll href="/calls/" label="All calls" />} />
      {state.loading && !state.data ? (
        <ListSkeleton />
      ) : state.error ? (
        <ErrorState error={state.error} onRetry={state.reload} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={PhoneCall}
          title="No calls yet"
          description="Calls appear here after someone phones the intake agent. Each call records its outcome, duration and transcript."
        />
      ) : (
        <ul className="divide-y divide-zinc-100">
          {items.map((c) => (
            <li key={c.id}>
              <Link
                href={`/calls/view/?id=${c.id}`}
                className="flex h-14 items-center justify-between gap-4 px-4 transition-colors duration-150 hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium tabular-nums text-zinc-900">{maskPhone(c.caller_number)}</p>
                  <p className="text-xs tabular-nums text-zinc-500">
                    {formatDuration(c.duration_seconds)} ·{" "}
                    <time dateTime={c.started_at ?? c.created_at} title={formatDateTime(c.started_at ?? c.created_at)}>
                      {timeAgo(c.started_at ?? c.created_at)}
                    </time>
                  </p>
                </div>
                <OutcomeBadge outcome={c.outcome} state={c.state} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
