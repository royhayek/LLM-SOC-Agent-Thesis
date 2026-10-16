import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuditRecord } from "../api/client";
import * as client from "../api/client";
import AuditLog from "./AuditLog";

vi.mock("../api/client");

const rec = (bundle: string, outcome: string, reason: string | null): AuditRecord => ({
  bundle_id: bundle, config_hash: "abcd1234ef", repetition: 0, node: "recommendation",
  attempt: 1, validator_outcome: outcome, rejection_reason: reason, policy_action: "emit",
  emitted: true, call_ref: `abcd1234ef:${bundle}:r0:recommendation`,
});

beforeEach(() => vi.resetAllMocks());

describe("AuditLog", () => {
  it("shows records with outcome, reason, bundle and condition", async () => {
    vi.mocked(client.getAudit).mockResolvedValue([rec("b1", "pass", null)]);
    render(<AuditLog onSelectIncident={() => {}} />);
    await waitFor(() => screen.getByText("b1"));
    expect(screen.getByRole("cell", { name: "pass" })).toBeInTheDocument(); // the row, not <option>
    expect(screen.getByText("abcd1234")).toBeInTheDocument(); // condition (config hash short)
  });

  it("filters by outcome would_reject", async () => {
    vi.mocked(client.getAudit).mockResolvedValue([rec("b2", "would_reject", "unknown_evidence")]);
    render(<AuditLog onSelectIncident={() => {}} />);
    fireEvent.change(screen.getByLabelText(/outcome/i), { target: { value: "would_reject" } });
    await waitFor(() => expect(client.getAudit).toHaveBeenCalledWith("would_reject"));
  });
});
