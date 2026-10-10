import { cn } from "@/lib/utils";

type Speaker = "agent" | "caller" | "other";

interface Turn {
  speaker: Speaker;
  text: string;
}

const PREFIXES: [RegExp, Speaker][] = [
  [/^(AI|Assistant|Agent|Bot)\s*:\s*/i, "agent"],
  [/^(User|Customer|Caller|Human)\s*:\s*/i, "caller"],
];

/** Parse "AI: ..." / "User: ..." lines; unprefixed lines continue the previous turn. */
export function parseTranscript(text: string): Turn[] {
  const turns: Turn[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const match = PREFIXES.find(([re]) => re.test(line));
    if (match) {
      turns.push({ speaker: match[1], text: line.replace(match[0], "") });
    } else if (turns.length > 0) {
      turns[turns.length - 1].text += ` ${line}`;
    } else {
      turns.push({ speaker: "other", text: line });
    }
  }
  return turns;
}

const LABEL: Record<Speaker, string> = { agent: "Agent", caller: "Caller", other: "" };

export function Transcript({ text }: { text: string }) {
  const turns = parseTranscript(text);
  return (
    <ol className="divide-y divide-zinc-100" aria-label="Call transcript">
      {turns.map((t, i) => (
        <li key={i} className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-3 px-4 py-2.5 sm:grid-cols-[5.5rem_minmax(0,1fr)]">
          <span
            className={cn(
              "pt-px text-xs font-medium uppercase tracking-wide",
              t.speaker === "agent" ? "text-teal-700" : "text-zinc-500",
            )}
          >
            {LABEL[t.speaker]}
          </span>
          <p className={cn("text-sm leading-6", t.speaker === "agent" ? "text-zinc-700" : "text-zinc-900")}>{t.text}</p>
        </li>
      ))}
    </ol>
  );
}
