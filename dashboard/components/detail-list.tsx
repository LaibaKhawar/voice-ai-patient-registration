import { cn } from "@/lib/utils";

export function DetailList({ children, className }: { children: React.ReactNode; className?: string }) {
  return <dl className={cn("divide-y divide-zinc-100", className)}>{children}</dl>;
}

export function DetailRow({ label, children, mono }: { label: string; children: React.ReactNode; mono?: boolean }) {
  const empty = children === null || children === undefined || children === "";
  return (
    <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-4 py-2.5 first:pt-0 last:pb-0">
      <dt className="text-[13px] text-zinc-500">{label}</dt>
      <dd className={cn("min-w-0 break-words text-sm", empty ? "text-zinc-400" : "text-zinc-900", mono && "tabular-nums")}>
        {empty ? "Not provided" : children}
      </dd>
    </div>
  );
}
