import { cn } from "../../lib/utils";

// Severity is the one place colour carries information. A withheld verdict has no severity.
const STYLES: Record<string, string> = {
  critical: "text-sev-critical border-sev-critical/40 bg-sev-critical/10",
  high: "text-sev-high border-sev-high/40 bg-sev-high/10",
  medium: "text-sev-medium border-sev-medium/40 bg-sev-medium/10",
  low: "text-sev-low border-sev-low/40 bg-sev-low/10",
};

export function SeverityBadge({ severity }: { severity: string | null | undefined }) {
  const key = severity ?? "";
  const style = STYLES[key] ?? "text-muted border-line-strong bg-panel-2";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        style,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {severity ?? "withheld"}
    </span>
  );
}
