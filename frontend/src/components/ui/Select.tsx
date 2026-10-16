import { ChevronDown } from "lucide-react";
import type { SelectHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

// A styled native select — keyboard- and screen-reader-accessible with no extra dependency.
export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative inline-flex">
      <select
        className={cn(
          "h-9 appearance-none rounded-md border border-line-strong bg-panel-2 pr-9 pl-3 text-sm",
          "text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute top-1/2 right-2.5 h-4 w-4 -translate-y-1/2 text-muted"
        aria-hidden
      />
    </div>
  );
}
