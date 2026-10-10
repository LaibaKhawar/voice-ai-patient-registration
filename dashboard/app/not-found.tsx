import Link from "next/link";
import { buttonClass } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh items-center justify-center px-4">
      <div className="text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">404</p>
        <h1 className="mt-2 text-[21px] font-semibold text-zinc-900">Page not found</h1>
        <p className="mt-1 text-sm text-zinc-500">The page you were looking for doesn&apos;t exist.</p>
        <Link href="/" className={buttonClass("secondary", "md", "mt-6")}>
          Back to overview
        </Link>
      </div>
    </div>
  );
}
