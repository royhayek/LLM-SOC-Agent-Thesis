import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/utils";

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-lg border border-line bg-panel", className)}
      {...props}
    />
  );
}

export function PanelHeader({ title, aside }: { title: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-line px-4 py-3">
      <h3 className="text-sm font-semibold tracking-tight text-text">{title}</h3>
      {aside}
    </div>
  );
}
