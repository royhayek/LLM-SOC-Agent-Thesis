// Typed client for the demo-simulator endpoints. Types come from the generated OpenAPI types, so a
// backend schema change breaks this at compile time. Read-only, plus the optional live-run SSE.
import { BASE } from "./client";
import type { components } from "./types";

export type Scenario = components["schemas"]["Scenario"];
export type DemoEvent = components["schemas"]["DemoEvent"];
export type ScenarioEvents = components["schemas"]["ScenarioEvents"];

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export const getScenarios = (): Promise<Scenario[]> => getJson<Scenario[]>("/demo/scenarios");

export const getScenarioEvents = (id: string, condition: string): Promise<ScenarioEvents> =>
  getJson<ScenarioEvents>(
    `/demo/scenarios/${encodeURIComponent(id)}?condition=${encodeURIComponent(condition)}`,
  );

export const liveTraceUrl = (bundleId: string, condition: string): string =>
  `${BASE}/demo/live/${encodeURIComponent(bundleId)}/trace?condition=${encodeURIComponent(condition)}`;
