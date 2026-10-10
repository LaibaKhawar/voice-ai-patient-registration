import type { Metadata } from "next";
import { Suspense } from "react";
import { PatientDetailView } from "./patient-detail-view";

export const metadata: Metadata = { title: "Patient" };

export default function PatientDetailPage() {
  return (
    <Suspense>
      <PatientDetailView />
    </Suspense>
  );
}
