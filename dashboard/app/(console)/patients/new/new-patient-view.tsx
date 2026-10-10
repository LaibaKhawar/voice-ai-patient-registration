"use client";

import { useRouter } from "next/navigation";
import { fullName } from "@/lib/format";
import { BackLink } from "@/components/back-link";
import { PageHeader } from "@/components/page-header";
import { PatientForm } from "@/components/patient-form";
import { useToast } from "@/components/ui/toast";

export function NewPatientView() {
  const router = useRouter();
  const { toast } = useToast();
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        eyebrow={<BackLink href="/patients/">Patients</BackLink>}
        title="New patient"
        description="Fields marked * are required."
      />
      <PatientForm
        onCancel={() => router.push("/patients/")}
        onSaved={(p) => {
          toast({ tone: "success", title: "Patient created", description: fullName(p) });
          router.push(`/patients/view/?id=${p.patient_id}`);
        }}
      />
    </div>
  );
}
