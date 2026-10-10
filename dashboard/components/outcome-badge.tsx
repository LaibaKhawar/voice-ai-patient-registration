import { Badge, type BadgeTone } from "./ui/badge";

const OUTCOMES: Record<string, { label: string; tone: BadgeTone }> = {
  registered: { label: "Registered", tone: "success" },
  updated: { label: "Updated", tone: "success" },
  abandoned: { label: "Abandoned", tone: "warning" },
  failed: { label: "Failed", tone: "danger" },
  no_registration: { label: "No registration", tone: "neutral" },
};

/** Outcome badge; falls back to the in-progress call state (e.g. "collecting"). */
export function OutcomeBadge({ outcome, state }: { outcome: string | null; state?: string }) {
  if (outcome && OUTCOMES[outcome]) {
    const o = OUTCOMES[outcome];
    return <Badge tone={o.tone}>{o.label}</Badge>;
  }
  const raw = outcome ?? state ?? "unknown";
  const label = raw === "collecting" || raw === "awaiting_confirmation" ? "In progress" : raw.replace(/_/g, " ");
  return <Badge tone="neutral">{label.charAt(0).toUpperCase() + label.slice(1)}</Badge>;
}

export function outcomeLabel(key: string) {
  return OUTCOMES[key]?.label ?? key.replace(/_/g, " ");
}
