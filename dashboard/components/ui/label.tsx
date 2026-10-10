import { cn } from "@/lib/utils";

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export function Label({ className, children, required, ...props }: LabelProps) {
  return (
    <label className={cn("mb-1.5 block text-[13px] font-medium text-zinc-800", className)} {...props}>
      {children}
      {required && (
        <>
          <span className="ml-0.5 text-rose-700" aria-hidden="true">
            *
          </span>
          <span className="sr-only"> (required)</span>
        </>
      )}
    </label>
  );
}
