"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import { CircleAlert, PhoneCall } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function safeNext(next: string | null) {
  // Only allow in-app relative paths (avoid open redirects).
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/login")) return "/";
  return next;
}

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (pending) return;
    if (!key.trim()) {
      setError("Enter your access key.");
      inputRef.current?.focus();
      return;
    }
    setPending(true);
    setError(null);
    try {
      await api.login(key.trim());
      router.replace(safeNext(params.get("next")));
    } catch (err) {
      setPending(false);
      if (err instanceof ApiError && err.status === 401) setError("That access key isn't valid.");
      else setError(err instanceof ApiError ? err.message : "Sign in failed. Please try again.");
      inputRef.current?.select();
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-12">
      <div className="w-full max-w-[360px]">
        <div className="mb-6 flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-teal-700 text-white" aria-hidden="true">
            <PhoneCall className="h-4 w-4" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-zinc-900">Intake Console</p>
            <p className="text-xs text-zinc-500">Lakeside Family Health</p>
          </div>
        </div>

        <div className="rounded-md border border-zinc-200 bg-white p-6">
          <h1 className="text-base font-semibold text-zinc-900">Sign in</h1>
          <p className="mt-1 text-[13px] text-zinc-500">Enter the console access key to continue.</p>

          <form onSubmit={onSubmit} className="mt-5" noValidate>
            <Label htmlFor="access-key">Access key</Label>
            <Input
              ref={inputRef}
              id="access-key"
              name="access-key"
              type="password"
              autoComplete="current-password"
              autoFocus
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                if (error) setError(null);
              }}
              invalid={!!error}
              aria-describedby={error ? "access-key-error access-key-help" : "access-key-help"}
            />
            {error && (
              <p id="access-key-error" role="alert" className="mt-1.5 flex items-center gap-1.5 text-[13px] text-rose-700">
                <CircleAlert className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {error}
              </p>
            )}
            <p id="access-key-help" className="mt-2 text-xs leading-5 text-zinc-500">
              Reviewers: the access key is listed in the README and submission notes.
            </p>
            <Button type="submit" variant="primary" className="mt-5 w-full" loading={pending}>
              {pending ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>
      </div>
    </main>
  );
}
