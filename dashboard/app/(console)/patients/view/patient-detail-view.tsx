"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ChevronRight, Pencil, PhoneCall, Trash2 } from "lucide-react";
import { api, ApiError, type Call } from "@/lib/api";
import {
  ageFromDob,
  formatCalendarDate,
  formatDateTime,
  formatDuration,
  formatPhone,
  fullName,
  timeAgo,
} from "@/lib/format";
import { US_STATES } from "@/lib/constants";
import { useQuery, type QueryState } from "@/lib/hooks";
import { BackLink } from "@/components/back-link";
import { CopyButton } from "@/components/copy-button";
import { DetailList, DetailRow } from "@/components/detail-list";
import { ErrorState } from "@/components/error-state";
import { PatientNotFound } from "@/components/not-found-state";
import { OutcomeBadge } from "@/components/outcome-badge";
import { PageHeader } from "@/components/page-header";
import { Button, buttonClass } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

const STATE_NAMES = Object.fromEntries(US_STATES);

export function PatientDetailView() {
  const id = useSearchParams().get("id") ?? "";
  const router = useRouter();
  const { toast } = useToast();
  const patientQ = useQuery(id ? `patient:${id}` : null, (s) => api.getPatient(id, s));
  const callsQ = useQuery(id ? `patient-calls:${id}` : null, (s) => api.patientCalls(id, s));
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (!id || patientQ.error?.isNotFound) return <PatientNotFound />;

  if (patientQ.error) {
    return (
      <Card>
        <ErrorState error={patientQ.error} onRetry={patientQ.reload} title="Couldn't load patient" />
      </Card>
    );
  }

  const p = patientQ.data;
  if (!p) return <DetailSkeleton />;

  async function onDelete() {
    if (!p) return;
    setDeleting(true);
    try {
      await api.deletePatient(p.patient_id);
      setConfirmOpen(false);
      toast({ tone: "success", title: "Patient deleted", description: `${fullName(p)} was removed from the patient list.` });
      router.push("/patients/");
    } catch (err) {
      setDeleting(false);
      setConfirmOpen(false);
      toast({
        tone: "error",
        title: "Couldn't delete patient",
        description: err instanceof ApiError ? err.message : undefined,
      });
    }
  }

  const age = ageFromDob(p.date_of_birth);

  return (
    <>
      <PageHeader
        eyebrow={<BackLink href="/patients/">Patients</BackLink>}
        title={fullName(p)}
        description={
          <div className="flex flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4">
            <span className="inline-flex items-center gap-1">
              <span className="text-zinc-500">ID</span>
              <code className="font-mono text-[12px] text-zinc-700">{p.patient_id}</code>
              <CopyButton value={p.patient_id} label="Copy patient ID" />
            </span>
            <span>
              Registered{" "}
              <time dateTime={p.created_at} className="tabular-nums text-zinc-700">
                {formatDateTime(p.created_at)}
              </time>
            </span>
            {p.updated_at !== p.created_at && (
              <span>
                Updated{" "}
                <time dateTime={p.updated_at} title={formatDateTime(p.updated_at)} className="tabular-nums text-zinc-700">
                  {timeAgo(p.updated_at)}
                </time>
              </span>
            )}
          </div>
        }
        actions={
          <>
            <Link href={`/patients/edit/?id=${p.patient_id}`} className={buttonClass("secondary", "md")}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              Edit
            </Link>
            <Button variant="danger-outline" onClick={() => setConfirmOpen(true)}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              Delete
            </Button>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Demographics" />
          <CardBody>
            <DetailList>
              <DetailRow label="First name">{p.first_name}</DetailRow>
              <DetailRow label="Last name">{p.last_name}</DetailRow>
              <DetailRow label="Date of birth" mono>
                {formatCalendarDate(p.date_of_birth)}
                {age !== null && <span className="text-zinc-500"> · {age} years</span>}
              </DetailRow>
              <DetailRow label="Sex">{p.sex}</DetailRow>
              <DetailRow label="Preferred language">{p.preferred_language}</DetailRow>
            </DetailList>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Contact" />
          <CardBody>
            <DetailList>
              <DetailRow label="Phone" mono>
                <a href={`tel:+1${p.phone_number}`} className="hover:underline">
                  {formatPhone(p.phone_number)}
                </a>
              </DetailRow>
              <DetailRow label="Email">
                {p.email && (
                  <a href={`mailto:${p.email}`} className="hover:underline">
                    {p.email}
                  </a>
                )}
              </DetailRow>
            </DetailList>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Address" />
          <CardBody>
            <DetailList>
              <DetailRow label="Street">{p.address_line_1}</DetailRow>
              <DetailRow label="Apt / unit">{p.address_line_2}</DetailRow>
              <DetailRow label="City">{p.city}</DetailRow>
              <DetailRow label="State">
                {STATE_NAMES[p.state] ? `${STATE_NAMES[p.state]} (${p.state})` : p.state}
              </DetailRow>
              <DetailRow label="ZIP code" mono>
                {p.zip_code}
              </DetailRow>
            </DetailList>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Insurance" />
          <CardBody>
            <DetailList>
              <DetailRow label="Provider">{p.insurance_provider}</DetailRow>
              <DetailRow label="Member ID" mono>
                {p.insurance_member_id}
              </DetailRow>
            </DetailList>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Emergency contact" />
          <CardBody>
            <DetailList>
              <DetailRow label="Name">{p.emergency_contact_name}</DetailRow>
              <DetailRow label="Phone" mono>
                {p.emergency_contact_phone && formatPhone(p.emergency_contact_phone)}
              </DetailRow>
            </DetailList>
          </CardBody>
        </Card>

        <CallHistory state={callsQ} />
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={onDelete}
        pending={deleting}
        destructive
        title={`Delete ${fullName(p)}?`}
        description={
          <>
            This will soft-delete <span className="font-medium text-zinc-900">{fullName(p)}</span>&apos;s record. It
            will no longer appear in the patient list. The record is retained in the database for audit purposes.
          </>
        }
        confirmLabel="Delete patient"
      />
    </>
  );
}

function CallHistory({ state }: { state: QueryState<Call[]> }) {
  const calls = state.data ?? [];
  return (
    <Card>
      <CardHeader title="Call history" description={state.data ? `${calls.length} linked ${calls.length === 1 ? "call" : "calls"}` : undefined} />
      {state.loading && !state.data ? (
        <div className="space-y-3 p-4" aria-hidden="true">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : state.error ? (
        <ErrorState error={state.error} onRetry={state.reload} title="Couldn't load calls" />
      ) : calls.length === 0 ? (
        <EmptyState
          icon={PhoneCall}
          title="No linked calls"
          description="This patient wasn't registered or updated through the voice agent."
          compact
        />
      ) : (
        <ul className="divide-y divide-zinc-100">
          {calls.map((c) => (
            <li key={c.id}>
              <Link
                href={`/calls/view/?id=${c.id}`}
                className="flex items-center gap-3 px-4 py-3 transition-colors duration-150 hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm tabular-nums text-zinc-900">{formatDateTime(c.started_at ?? c.created_at)}</p>
                  <p className="text-xs tabular-nums text-zinc-500">
                    {c.mode === "update" ? "Update call" : "Registration call"} · {formatDuration(c.duration_seconds)}
                  </p>
                </div>
                <OutcomeBadge outcome={c.outcome} state={c.state} />
                <ChevronRight className="h-4 w-4 shrink-0 text-zinc-400" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function DetailSkeleton() {
  return (
    <div aria-hidden="true">
      <div className="mb-6 space-y-2">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-3.5 w-80 max-w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-44 w-full" />
        ))}
      </div>
    </div>
  );
}

