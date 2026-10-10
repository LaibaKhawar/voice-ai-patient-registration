"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { fullName } from "@/lib/format";
import { useQuery } from "@/lib/hooks";
import { BackLink } from "@/components/back-link";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { PatientForm } from "@/components/patient-form";
import { PatientNotFound } from "@/components/not-found-state";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

export function EditPatientView() {
  const router = useRouter();
  const id = useSearchParams().get("id") ?? "";
  const { toast } = useToast();
  const { data: patient, error, loading, reload } = useQuery(id ? `patient:${id}` : null, (s) => api.getPatient(id, s));
  const detailHref = `/patients/view/?id=${id}`;

  if (!id || error?.isNotFound) return <PatientNotFound />;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        eyebrow={<BackLink href={patient ? detailHref : "/patients/"}>{patient ? fullName(patient) : "Patients"}</BackLink>}
        title={patient ? `Edit ${fullName(patient)}` : "Edit patient"}
        description="Only changed fields are saved. Fields marked * are required."
      />
      {error ? (
        <Card>
          <ErrorState error={error} onRetry={reload} title="Couldn't load patient" />
        </Card>
      ) : loading || !patient ? (
        <div className="space-y-6" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : (
        <PatientForm
          key={patient.patient_id}
          patient={patient}
          onCancel={() => router.push(detailHref)}
          onSaved={(p, changed) => {
            toast({
              tone: "success",
              title: changed ? "Changes saved" : "No changes to save",
              description: fullName(p),
            });
            router.push(detailHref);
          }}
        />
      )}
    </div>
  );
}
