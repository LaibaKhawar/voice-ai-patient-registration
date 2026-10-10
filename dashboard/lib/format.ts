/** Display formatting helpers. All dates use Intl in the viewer's locale/time zone. */

const dateTimeFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});
const dateFmt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });
const dateUtcFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});
const shortDayUtcFmt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const rtf = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });
const numberFmt = new Intl.NumberFormat("en-US");

export function formatNumber(n: number) {
  return numberFmt.format(n);
}

export function formatDateTime(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : dateTimeFmt.format(d);
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : dateFmt.format(d);
}

/** Calendar dates (YYYY-MM-DD) are formatted in UTC so they never shift a day. */
export function formatCalendarDate(ymd: string | null | undefined) {
  if (!ymd) return "—";
  const d = new Date(`${ymd}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? ymd : dateUtcFmt.format(d);
}

export function formatShortDay(ymd: string) {
  const d = new Date(`${ymd}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? ymd : shortDayUtcFmt.format(d);
}

export function timeAgo(iso: string | null | undefined, now: number = Date.now()) {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const diff = (t - now) / 1000;
  const abs = Math.abs(diff);
  if (abs < 45) return "just now";
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["minute", 60],
    ["hour", 3600],
    ["day", 86400],
    ["week", 604800],
    ["month", 2629800],
    ["year", 31557600],
  ];
  let chosen: [Intl.RelativeTimeFormatUnit, number] = units[0];
  for (const u of units) if (abs >= u[1]) chosen = u;
  return rtf.format(Math.round(diff / chosen[1]), chosen[0]);
}

export function ageFromDob(ymd: string, today: Date = new Date()) {
  const [y, m, d] = ymd.split("-").map(Number);
  if (!y || !m || !d) return null;
  let age = today.getFullYear() - y;
  const beforeBirthday = today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d);
  if (beforeBirthday) age -= 1;
  return age >= 0 ? age : null;
}

export function digitsOnly(s: string) {
  return s.replace(/\D/g, "");
}

/** 5125550142 -> (512) 555-0142. Leaves other shapes untouched. */
export function formatPhone(phone: string | null | undefined) {
  if (!phone) return "—";
  let d = digitsOnly(phone);
  if (d.length === 11 && d.startsWith("1")) d = d.slice(1);
  if (d.length !== 10) return phone;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}

/** +15125550142 -> •••-•••-0142 */
export function maskPhone(phone: string | null | undefined) {
  if (!phone) return "Unknown";
  const d = digitsOnly(phone);
  if (d.length < 4) return "Unknown";
  return `•••-•••-${d.slice(-4)}`;
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined || seconds < 0) return "—";
  const s = Math.round(seconds);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

const ENDED_REASONS: Record<string, string> = {
  "customer-ended-call": "Caller hung up",
  "assistant-ended-call": "Agent ended call",
  "assistant-said-end-call-phrase": "Agent ended call",
  "assistant-forwarded-call": "Transferred",
  "silence-timed-out": "Silence timeout",
  "exceeded-max-duration": "Max duration reached",
  "customer-did-not-answer": "No answer",
  "customer-busy": "Line busy",
  voicemail: "Reached voicemail",
  "assistant-error": "Agent error",
  "manually-canceled": "Canceled",
};

export function humanizeEndedReason(reason: string | null | undefined) {
  if (!reason) return "—";
  if (ENDED_REASONS[reason]) return ENDED_REASONS[reason];
  if (reason.startsWith("pipeline-error") || reason.includes("error")) return "System error";
  const text = reason.replace(/[-_.]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function humanizeToken(s: string | null | undefined) {
  if (!s) return "—";
  const text = s.replace(/[-_]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function fullName(p: { first_name: string; last_name: string }) {
  return `${p.first_name} ${p.last_name}`;
}

export function listName(p: { first_name: string; last_name: string }) {
  return `${p.last_name}, ${p.first_name}`;
}
