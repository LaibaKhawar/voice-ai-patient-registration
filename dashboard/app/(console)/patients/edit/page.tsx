import type { Metadata } from "next";
import { Suspense } from "react";
import { EditPatientView } from "./edit-patient-view";

export const metadata: Metadata = { title: "Edit patient" };

export default function EditPatientPage() {
  return (
    <Suspense>
      <EditPatientView />
    </Suspense>
  );
}
