// Typed client for the localhost SOC console API. All types come from the generated OpenAPI
// types (./types.ts), so a backend schema change breaks this file at compile time (§6.2). The
// console only reads, plus the single accept/reject write; it never acts on the testbed (§1.1).
import type { components } from "./types";

export type Incident = components["schemas"]["Incident"];
export type Verdict = components["schemas"]["Verdict"];
export type AuditRecord = components["schemas"]["AuditRecord"];
export type DecisionIn = components["schemas"]["DecisionIn"];
export type DecisionOut = components["schemas"]["DecisionOut"];

// The dev server proxies /api to the 127.0.0.1 API (vite.config.ts); tests stub fetch.
export const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export const getConditions = (): Promise<string[]> => getJson<string[]>("/conditions");

export const getIncidents = (condition: string): Promise<Incident[]> =>
  getJson<Incident[]>(`/incidents?condition=${encodeURIComponent(condition)}`);

export const getIncident = (id: string, condition: string): Promise<Incident> =>
  getJson<Incident>(
    `/incidents/${encodeURIComponent(id)}?condition=${encodeURIComponent(condition)}`,
  );

export const getAudit = (outcome?: string): Promise<AuditRecord[]> =>
  getJson<AuditRecord[]>(`/audit${outcome ? `?outcome=${encodeURIComponent(outcome)}` : ""}`);

export async function getReport(id: string): Promise<string> {
  const res = await fetch(`${BASE}/reports/${encodeURIComponent(id)}`);
  if (res.status === 404) return "";
  if (!res.ok) throw new Error(`report ${id} failed: ${res.status}`);
  return res.text();
}

export async function postDecision(id: string, body: DecisionIn): Promise<DecisionOut> {
  const res = await fetch(`${BASE}/incidents/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`decision failed: ${res.status}`);
  return (await res.json()) as DecisionOut;
}

export const traceUrl = (id: string, condition: string): string =>
  `${BASE}/incidents/${encodeURIComponent(id)}/trace?condition=${encodeURIComponent(condition)}`;
