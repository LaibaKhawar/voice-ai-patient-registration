import { ChevronLeft, ChevronRight } from "lucide-react";
import { formatNumber } from "@/lib/format";
import { Button } from "./ui/button";

export function Pagination({
  offset,
  limit,
  total,
  onPage,
  noun = "results",
}: {
  offset: number;
  limit: number;
  total: number;
  onPage: (offset: number) => void;
  noun?: string;
}) {
  if (total === 0) return null;
  const from = Math.min(offset + 1, total);
  const to = Math.min(offset + limit, total);
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  return (
    <nav
      aria-label="Pagination"
      className="flex items-center justify-between gap-3 border-t border-zinc-200 px-4 py-2.5 text-[13px] text-zinc-600"
    >
      <p className="tabular-nums">
        Showing <span className="font-medium text-zinc-900">{formatNumber(from)}</span>–
        <span className="font-medium text-zinc-900">{formatNumber(to)}</span> of{" "}
        <span className="font-medium text-zinc-900">{formatNumber(total)}</span> {noun}
      </p>
      <div className="flex items-center gap-2">
        <span className="hidden tabular-nums text-zinc-500 sm:inline">
          Page {page} of {pages}
        </span>
        <Button size="icon" variant="secondary" onClick={() => onPage(Math.max(0, offset - limit))} disabled={offset === 0} aria-label="Previous page">
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </Button>
        <Button size="icon" variant="secondary" onClick={() => onPage(offset + limit)} disabled={to >= total} aria-label="Next page">
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
