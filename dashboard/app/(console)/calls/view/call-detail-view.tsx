"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CircleAlert, FileText, UserRound } from "lucide-react";
import { api } from "@/lib/api";
import {
  formatDateTime,
  formatDuration,
  humanizeEndedReason,
  humanizeToken,
  maskPhone,
} from "@/lib/format";
import { useQuery } from "@/lib/hooks";
import { BackLink } from "@/components/back-link";
import { CopyButton } from "@/components/copy-button";
import { ErrorState } from "@/components/error-state";
import { CallNotFound } from "@/components/not-found-state";
import { OutcomeBadge } from "@/components/outcome-badge";
import { PageHeader } from "@/components/page-header";
import { Transcript } from "@/components/transcript";
import { buttonClass } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

export function CallDetailView() {
  const id = useSearchParams().get("id") ?? "";
  const { data: call, error, reload } = useQuery(id ? `call:${id}` : null, (s) => api.getCall(id, s));

  if (!id || error?.isNotFound) return <CallNotFound />;
  if (error) {
    return (
      <Card>
        <ErrorState error={error} onRetry={reload} title="Couldn't load call" />
      </Card>
    );
  }
  if (!call) {
    return (
      <div aria-hidden="true" className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-7 w-64" />
        </div>
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  const started = call.started_at ?? call.created_at;
  const meta: [string, React.ReactNode][] = [
    ["Started", formatDateTime(started)],
    ["Ended", formatDateTime(call.ended_at)],
    ["Duration", formatDuration(call.duration_seconds)],
    ["Caller", maskPhone(call.caller_number)],
    ["Mode", call.mode === "update" ? "Update existing record" : "New registration"],
    ["Ended reason", humanizeEndedReason(call.ended_reason)],
    ["State", humanizeToken(call.state)],
    [
      "Vapi call ID",
      <span key="vapi" className="inline-flex min-w-0 items-center gap-1">
        <code className="truncate font-mono text-[12px]">{call.vapi_call_id}</code>
        <CopyButton value={call.vapi_call_id} label="Copy Vapi call ID" />
      </span>,
    ],
  ];

  return (
    <>
      <PageHeader
        eyebrow={<BackLink href="/calls/">Calls</BackLink>}
        title={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="tabular-nums">Call on {formatDateTime(started)}</span>
            <OutcomeBadge outcome={call.outcome} state={call.state} />
          </span>
        }
        description={`${maskPhone(call.caller_number)} · ${formatDuration(call.duration_seconds)}`}
        actions={
          call.patient_id ? (
            <Link href={`/patients/view/?id=${call.patient_id}`} className={buttonClass("secondary", "md")}>
              <UserRound className="h-4 w-4" aria-hidden="true" />
              View patient
            </Link>
          ) : undefined
        }
      />

      {call.last_error && (
        <div
          role="note"
          className="mb-6 flex items-start gap-2.5 rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-700"
        >
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-zinc-500" aria-hidden="true" />
          <div className="min-w-0">
            <p className="font-medium text-zinc-900">Last error during this call</p>
            <p className="mt-0.5 break-words text-[13px] text-zinc-600">{call.last_error}</p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Details" />
            <CardBody>
              <dl className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-1">
                {meta.map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-xs text-zinc-500">{label}</dt>
                    <dd className="mt-0.5 min-w-0 text-sm tabular-nums text-zinc-900">{value}</dd>
                  </div>
                ))}
                <div className="min-w-0">
                  <dt className="text-xs text-zinc-500">Patient</dt>
                  <dd className="mt-0.5 text-sm">
                    {call.patient_id ? (
                      <Link
                        href={`/patients/view/?id=${call.patient_id}`}
                        className="rounded font-medium text-teal-700 hover:text-teal-900 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                      >
                        View linked patient
                      </Link>
                    ) : (
                      <span className="text-zinc-400">No linked patient</span>
                    )}
                  </dd>
                </div>
              </dl>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Summary" />
            <CardBody>
              {call.summary ? (
                <p className="whitespace-pre-line text-sm leading-6 text-zinc-700">{call.summary}</p>
              ) : (
                <p className="text-[13px] text-zinc-400">No summary was generated for this call.</p>
              )}
            </CardBody>
          </Card>
        </div>

        <Card>
          <CardHeader title="Transcript" />
          {call.transcript ? (
            <Transcript text={call.transcript} />
          ) : (
            <EmptyState
              icon={FileText}
              title="No transcript"
              description="A transcript is attached when the call ends. In-progress or dropped calls may not have one."
            />
          )}
        </Card>
      </div>
    </>
  );
}
