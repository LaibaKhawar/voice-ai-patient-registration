"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { LayoutGrid, LogOut, Menu, PhoneCall, Users, X } from "lucide-react";
import { api, ApiError, redirectToLogin } from "@/lib/api";
import { useFocusTrap } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Skeleton } from "./ui/skeleton";
import { useToast } from "./ui/toast";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutGrid, match: (p: string) => p === "/" },
  { href: "/patients/", label: "Patients", icon: Users, match: (p: string) => p.startsWith("/patients") },
  { href: "/calls/", label: "Calls", icon: PhoneCall, match: (p: string) => p.startsWith("/calls") },
];

type AuthState = "checking" | "ok" | "error";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>("checking");
  const [authError, setAuthError] = useState<string>("");
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();

  const checkSession = useCallback((signal?: AbortSignal) => {
    setAuth("checking");
    api
      .session(signal)
      .then(() => setAuth("ok"))
      .catch((err: unknown) => {
        if (signal?.aborted) return;
        // 401 already triggered a redirect to /login inside the API client.
        if (err instanceof ApiError && err.status === 401) return;
        setAuthError(err instanceof ApiError ? err.message : "Could not reach the server.");
        setAuth("error");
      });
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    checkSession(ctrl.signal);
    return () => ctrl.abort();
  }, [checkSession]);

  // Close the mobile menu on navigation.
  useEffect(() => setMenuOpen(false), [pathname]);

  if (auth === "checking") {
    return (
      <div className="flex min-h-dvh items-center justify-center" role="status" aria-live="polite">
        <span className="sr-only">Checking your session…</span>
        <div className="w-48 space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
    );
  }

  if (auth === "error") {
    return (
      <div className="flex min-h-dvh items-center justify-center px-4">
        <div role="alert" className="w-full max-w-sm rounded-md border border-zinc-200 bg-white p-6 text-center">
          <p className="text-sm font-medium text-zinc-900">Unable to connect</p>
          <p className="mt-1 text-[13px] text-zinc-500">{authError}</p>
          <button
            type="button"
            onClick={() => checkSession()}
            className="mt-4 inline-flex h-8 items-center rounded-md border border-zinc-300 px-3 text-[13px] font-medium text-zinc-900 transition-colors duration-150 hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh lg:pl-60">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-white px-3 py-2 text-sm focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:ring-2 focus:ring-teal-600"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-zinc-200 bg-white lg:flex">
        <SidebarContents pathname={pathname} />
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-zinc-200 bg-white px-4 lg:hidden">
        <Brand />
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-zinc-700 transition-colors duration-150 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
          aria-label="Open navigation menu"
          aria-expanded={menuOpen}
          aria-controls="mobile-nav"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>
      <MobileSheet open={menuOpen} onClose={() => setMenuOpen(false)} pathname={pathname} />

      <main id="main" className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        {children}
      </main>
    </div>
  );
}

function Brand() {
  return (
    <Link href="/" className="group flex items-center gap-2.5 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600">
      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-teal-700 text-white" aria-hidden="true">
        <PhoneCall className="h-3.5 w-3.5" />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold text-zinc-900">Intake Console</span>
        <span className="block text-[11px] text-zinc-500">Lakeside Family Health</span>
      </span>
    </Link>
  );
}

function SidebarContents({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center px-4">
        <Brand />
      </div>
      <nav aria-label="Main" className="flex-1 px-3 py-2">
        <ul className="space-y-0.5">
          {NAV.map((item) => {
            const active = item.match(pathname);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex h-8 items-center gap-2.5 rounded-md px-2.5 text-[13px] font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600",
                    active ? "bg-teal-50 text-teal-800" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900",
                  )}
                >
                  <Icon className={cn("h-4 w-4", active ? "text-teal-700" : "text-zinc-400")} aria-hidden="true" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="space-y-1 border-t border-zinc-200 p-3">
        <SystemStatus />
        <SignOutButton />
      </div>
    </div>
  );
}

function MobileSheet({ open, onClose, pathname }: { open: boolean; onClose: () => void; pathname: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <div className="absolute inset-0 bg-zinc-950/40" aria-hidden="true" onClick={onClose} />
      <div
        ref={ref}
        id="mobile-nav"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-zinc-200 bg-white"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3.5 inline-flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 transition-colors duration-150 hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
          aria-label="Close navigation menu"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
        <SidebarContents pathname={pathname} onNavigate={onClose} />
      </div>
    </div>
  );
}

type Readiness = "checking" | "ok" | "down";

function SystemStatus() {
  const [status, setStatus] = useState<Readiness>("checking");

  useEffect(() => {
    let cancelled = false;
    let ctrl = new AbortController();
    const check = () => {
      ctrl.abort();
      ctrl = new AbortController();
      api
        .ready(ctrl.signal)
        .then(() => !cancelled && setStatus("ok"))
        .catch((err: unknown) => {
          if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
          setStatus("down");
        });
    };
    check();
    const interval = setInterval(check, 60_000);
    return () => {
      cancelled = true;
      ctrl.abort();
      clearInterval(interval);
    };
  }, []);

  const meta = {
    checking: { dot: "bg-zinc-300", text: "Checking status…" },
    ok: { dot: "bg-emerald-500", text: "All systems operational" },
    down: { dot: "bg-rose-500", text: "Database unavailable" },
  }[status];

  return (
    <div className="flex h-8 items-center gap-2.5 px-2.5 text-[13px] text-zinc-600" role="status" aria-live="polite">
      <span className={cn("h-2 w-2 shrink-0 rounded-full", meta.dot)} aria-hidden="true" />
      <span className="truncate">{meta.text}</span>
    </div>
  );
}

function SignOutButton() {
  const [pending, setPending] = useState(false);
  const { toast } = useToast();

  async function signOut() {
    setPending(true);
    try {
      await api.logout();
      redirectToLogin(false);
    } catch (err) {
      setPending(false);
      toast({
        tone: "error",
        title: "Sign out failed",
        description: err instanceof ApiError ? err.message : undefined,
      });
    }
  }

  return (
    <button
      type="button"
      onClick={signOut}
      disabled={pending}
      className="flex h-8 w-full items-center gap-2.5 rounded-md px-2.5 text-[13px] font-medium text-zinc-600 transition-colors duration-150 hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 disabled:opacity-50"
    >
      <LogOut className="h-4 w-4 text-zinc-400" aria-hidden="true" />
      {pending ? "Signing out…" : "Sign out"}
    </button>
  );
}
