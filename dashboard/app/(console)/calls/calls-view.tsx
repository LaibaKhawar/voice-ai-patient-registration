"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronRight, PhoneCall } from "lucide-react";
import { api, type Call } from "@/lib/api";
import { CALL_PAGE_SIZE } from "@/lib/constants";
import { formatDateTime, formatDuration, formatNumber, humanizeEndedReason, maskPhone, timeAgo } from "@/lib/format";
import { useQuery } from "@/lib/hooks";
import { ErrorState } from "@/components/error-state";
import { OutcomeBadge } from "@/components/outcome-badge";
import { PageHeader } from "@/components/page-header";
import { Pagination } from "@/components/pagination";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export function CallsView() {
  const router = useRouter();
  const params = useSearchParams();
  const page = Math.max(1, Number.parseInt(params.get("page") ?? "1", 10) || 1);
  const offset = (page - 1) * CALL_PAGE_SIZE;
  const { data, error, loading, reload } = useQuery(`calls:${offset}`, (s) =>
    api.listCalls({ limit: CALL_PAGE_SIZE, offset }, s),
  );
  const calls = data?.items ?? [];
  const total = data?.meta.total ?? 0;

  return (
    <>
      <PageHeader
        title="Calls"
        description={data ? `${formatNumber(total)} ${total === 1 ? "call" : "calls"} handled by the voice agent` : " "}
      />
      <Card>
        <div aria-live="polite" aria-busy={loading}>
          {error ? (
            <ErrorState error={error} onRetry={reload} title="Couldn't load calls" />
          ) : loading && !data ? (
            <CallsSkeleton />
          ) : calls.length === 0 ? (
            <EmptyState
              icon={PhoneCall}
              title="No calls yet"
              description="Calls appear here after someone phones the intake agent. Each record includes the outcome, duration, summary and transcript."
            />
          ) : (
            <div className={loading ? "opacity-60 transition-opacity duration-150" : "transition-opacity duration-150"}>
              <div className="hidden md:block">
                <Table>
                  <THead>
                    <tr>
                      <TH>Started</TH>
                      <TH>Caller</TH>
                      <TH className="text-right">Duration</TH>
                      <TH>Outcome</TH>
                      <TH>Patient</TH>
                      <TH>Ended reason</TH>
                    </tr>
                  </THead>
                  <TBody>
                    {calls.map((c) => (
                      <TR
                        key={c.id}
                        className="cursor-pointer transition-colors duration-150 hover:bg-zinc-50"
                        onClick={(e) => {
                          if ((e.target as HTMLElement).closest("a")) return;
                          router.push(`/calls/view/?id=${c.id}`);
                        }}
                      >
                        <TD>
                          <Link
                            href={`/calls/view/?id=${c.id}`}
                            className="rounded font-medium tabular-nums text-zinc-900 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                            title={timeAgo(c.started_at ?? c.created_at)}
                          >
                            {formatDateTime(c.started_at ?? c.created_at)}
                          </Link>
                        </TD>
                        <TD className="tabular-nums">{maskPhone(c.caller_number)}</TD>
                        <TD className="text-right tabular-nums">{formatDuration(c.duration_seconds)}</TD>
                        <TD>
                          <OutcomeBadge outcome={c.outcome} state={c.state} />
                        </TD>
                        <TD>
                          <PatientLink call={c} />
                        </TD>
                        <TD className="text-zinc-500">{humanizeEndedReason(c.ended_reason)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
              <ul className="divide-y divide-zinc-200 md:hidden">
                {calls.map((c) => (
                  <li key={c.id}>
                    <Link
                      href={`/calls/view/?id=${c.id}`}
                      className="flex items-center gap-3 px-4 py-3 transition-colors duration-150 hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-3">
                          <p className="truncate text-sm font-medium tabular-nums text-zinc-900">
                            {formatDateTime(c.started_at ?? c.created_at)}
                          </p>
                          <OutcomeBadge outcome={c.outcome} state={c.state} />
                        </div>
                        <p className="mt-0.5 text-[13px] tabular-nums text-zinc-500">
                          {maskPhone(c.caller_number)} · {formatDuration(c.duration_seconds)} ·{" "}
                          {humanizeEndedReason(c.ended_reason)}
                        </p>
                      </div>
                      <ChevronRight className="h-4 w-4 shrink-0 text-zinc-400" aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        {data && !error && (
          <Pagination
            offset={offset}
            limit={CALL_PAGE_SIZE}
            total={total}
            noun={total === 1 ? "call" : "calls"}
            onPage={(next) => {
              const p = next / CALL_PAGE_SIZE + 1;
              router.replace(p > 1 ? `/calls/?page=${p}` : "/calls/", { scroll: false });
              window.scrollTo({ top: 0 });
            }}
          />
        )}
      </Card>
    </>
  );
}

function PatientLink({ call }: { call: Call }) {
  if (!call.patient_id) return <span className="text-zinc-400">—</span>;
  return (
    <Link
      href={`/patients/view/?id=${call.patient_id}`}
      className="rounded font-medium text-teal-700 hover:text-teal-900 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
    >
      View patient
    </Link>
  );
}

function CallsSkeleton() {
  return (
    <div aria-hidden="true">
      <div className="hidden h-9 border-b border-zinc-200 bg-zinc-50 md:block" />
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex h-11 items-center gap-6 border-b border-zinc-200 px-4 last:border-b-0">
          <Skeleton className="h-3.5 w-36" />
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="hidden h-3.5 w-10 md:block" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="hidden h-3.5 w-20 md:block" />
        </div>
      ))}
    </div>
  );
}
