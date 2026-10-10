import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export function BackLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="-ml-1 inline-flex items-center gap-0.5 rounded px-1 text-[13px] font-medium text-zinc-500 transition-colors duration-150 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
    >
      <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
      {children}
    </Link>
  );
}
