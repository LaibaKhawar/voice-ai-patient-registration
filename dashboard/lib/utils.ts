export type ClassValue = string | false | null | undefined | 0;

/** Minimal className joiner (no tailwind-merge; callers avoid conflicting utilities). */
export function cn(...classes: ClassValue[]) {
  return classes.filter(Boolean).join(" ");
}
