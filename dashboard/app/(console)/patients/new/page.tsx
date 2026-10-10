import type { Metadata } from "next";
import { NewPatientView } from "./new-patient-view";

export const metadata: Metadata = { title: "New patient" };

export default function NewPatientPage() {
  return <NewPatientView />;
}
