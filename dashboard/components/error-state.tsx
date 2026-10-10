import { CircleAlert, RotateCw } from "lucide-react";
import type { ApiError } from "@/lib/api";
import { Button } from "./ui/button";

export function ErrorState({
  error,
  onRetry,
  title = "Couldn't load data",
}: {
  error: ApiError | null;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md border border-rose-200 bg-rose-50">
        <CircleAlert className="h-4 w-4 text-rose-600" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium text-zinc-900">{title}</p>
      <p className="mt-1 max-w-sm text-[13px] text-zinc-500">
        {error?.message ?? "Something went wrong."}
      </p>
      {onRetry && (
        <Button size="sm" className="mt-4" onClick={onRetry}>
          <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
          Try again
        </Button>
      )}
    </div>
  );
}
