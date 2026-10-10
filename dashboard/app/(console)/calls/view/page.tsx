import type { Metadata } from "next";
import { Suspense } from "react";
import { CallDetailView } from "./call-detail-view";

export const metadata: Metadata = { title: "Call" };

export default function CallDetailPage() {
  return (
    <Suspense>
      <CallDetailView />
    </Suspense>
  );
}
