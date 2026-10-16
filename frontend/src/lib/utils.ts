import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const SEVERITY = ["critical", "high", "medium", "low"] as const;
export type Severity = (typeof SEVERITY)[number];

export function severityRank(sev: string | null | undefined): number {
  const i = SEVERITY.indexOf((sev ?? "") as Severity);
  return i === -1 ? 99 : i;
}
