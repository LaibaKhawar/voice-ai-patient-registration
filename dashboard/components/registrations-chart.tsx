"use client";

import { useId, useState } from "react";
import { formatCalendarDate, formatShortDay } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Point {
  date: string;
  count: number;
}

/** Pick a "nice" axis max ≥ value so gridlines land on round numbers. */
function niceMax(v: number) {
  if (v <= 4) return 4;
  const pow = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 2, 2.5, 5, 10]) {
    const candidate = m * pow;
    if (candidate >= v && Number.isInteger(candidate / 4)) return candidate;
  }
  return Math.ceil(v / 4) * 4;
}

/**
 * Single-series bar chart of daily registrations. Div-based so text stays crisp at
 * any width. Each bar has a hover/focus tooltip and a title attribute; a visually
 * hidden table carries the same data for screen readers.
 */
export function RegistrationsChart({ data }: { data: Point[] }) {
  const [active, setActive] = useState<number | null>(null);
  const titleId = useId();
  const total = data.reduce((s, d) => s + d.count, 0);
  const max = niceMax(Math.max(0, ...data.map((d) => d.count)));
  const ticks = [max, (max * 3) / 4, max / 2, max / 4, 0];
  const first = data[0]?.date;
  const last = data[data.length - 1]?.date;

  return (
    <figure aria-labelledby={titleId} className="m-0">
      <figcaption id={titleId} className="sr-only">
        Patient registrations per day, {first ? formatCalendarDate(first) : ""} to{" "}
        {last ? formatCalendarDate(last) : ""}. {total} total.
      </figcaption>

      <div className="flex gap-3" aria-hidden="true">
        {/* Y axis */}
        <div className="relative h-48 w-6 shrink-0 text-right text-[11px] tabular-nums text-zinc-400">
          {ticks.map((t, i) => (
            <span key={i} className="absolute right-0 -translate-y-1/2" style={{ top: `${(i / 4) * 100}%` }}>
              {Number.isInteger(t) ? t : t.toFixed(1)}
            </span>
          ))}
        </div>

        <div className="relative min-w-0 flex-1">
          {/* Gridlines */}
          <div className="pointer-events-none absolute inset-x-0 top-0 h-48">
            {ticks.map((_, i) => (
              <div
                key={i}
                className={cn("absolute inset-x-0 border-t", i === 4 ? "border-zinc-300" : "border-dashed border-zinc-100")}
                style={{ top: `${(i / 4) * 100}%` }}
              />
            ))}
          </div>

          {/* Bars */}
          <div className="relative flex h-48 items-end gap-[2px] sm:gap-1">
            {data.map((d, i) => {
              const pct = max === 0 ? 0 : (d.count / max) * 100;
              const label = `${formatCalendarDate(d.date)}: ${d.count} registration${d.count === 1 ? "" : "s"}`;
              return (
                <div
                  key={d.date}
                  className="group relative flex h-full flex-1 items-end justify-center"
                  title={label}
                  onMouseEnter={() => setActive(i)}
                  onMouseLeave={() => setActive((a) => (a === i ? null : a))}
                >
                  <div
                    className={cn(
                      "w-full max-w-7 transition-colors duration-150",
                      d.count === 0
                        ? "h-px bg-zinc-300"
                        : cn("rounded-t-[4px]", active === i ? "bg-teal-800" : "bg-teal-700"),
                    )}
                    style={d.count === 0 ? undefined : { height: `${Math.max(pct, 1.5)}%` }}
                  />
                  {active === i && (
                    <div
                      className={cn(
                        "pointer-events-none absolute bottom-full z-10 mb-1 whitespace-nowrap rounded border border-zinc-200 bg-white px-2 py-1 text-xs shadow-sm",
                        i < 2 ? "left-0" : i > data.length - 3 ? "right-0" : "left-1/2 -translate-x-1/2",
                      )}
                      style={{ bottom: `${Math.max(pct, 0)}%` }}
                    >
                      <span className="text-zinc-500">{formatShortDay(d.date)}</span>{" "}
                      <span className="font-medium tabular-nums text-zinc-900">{d.count}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* X axis labels: thinned on narrow screens, aligned so the latest day is always labeled */}
          <div className="mt-2 flex gap-[2px] text-[11px] tabular-nums text-zinc-400 sm:gap-1">
            {data.map((d, i) => {
              const fromEnd = data.length - 1 - i;
              return (
                <div key={d.date} className="flex flex-1 justify-center whitespace-nowrap">
                  <span
                    className={cn(
                      fromEnd % 6 === 0 ? "inline" : fromEnd % 2 === 0 ? "hidden sm:inline" : "hidden xl:inline",
                    )}
                  >
                    {formatShortDay(d.date)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p className="mt-1 pl-9 text-[11px] text-zinc-400" aria-hidden="true">
        Registrations per day (UTC)
      </p>

      <table className="sr-only">
        <caption>Registrations per day</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Registrations</th>
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.date}>
              <td>{formatCalendarDate(d.date)}</td>
              <td>{d.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
