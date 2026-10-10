import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export const fieldBase =
  "block w-full rounded-md border bg-white text-sm text-zinc-900 placeholder:text-zinc-400 " +
  "transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-teal-600/30 focus:border-teal-600 " +
  "disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  /** Leaves room for an absolutely positioned leading icon. */
  leadingIcon?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ className, invalid, leadingIcon, ...props }, ref) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        fieldBase,
        "h-9",
        leadingIcon ? "pl-9 pr-3" : "px-3",
        invalid ? "border-rose-500 focus:border-rose-600 focus:ring-rose-600/20" : "border-zinc-300",
        className,
      )}
      {...props}
    />
  );
});
