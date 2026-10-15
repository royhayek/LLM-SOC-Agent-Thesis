"""Tests for cost and latency per incident (E9-07, SCRUM-101)."""

from __future__ import annotations

from pathlib import Path

import pytest

from thesis.eval.cost import (
    PRICE_DATE,
    USD_PER_EUR,
    cost_per_incident,
    row_eur,
    write_cost_csv,
)


def _row(cfg: str, tokens_in: int, tokens_out: int, latency_ms: float) -> dict[str, object]:
    return {
        "config_hash": cfg,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
    }


def test_row_eur_equals_hand_computed() -> None:
    # 1M input + 1M output = USD 0.02 + 0.04 = 0.06; euros = 0.06 / 1.1225.
    assert row_eur(1_000_000, 1_000_000) == pytest.approx(0.06 / USD_PER_EUR)
    assert row_eur(0, 0) == 0.0


def test_cost_per_incident_hand_computed() -> None:
    rows = [
        _row("c1", 1_000_000, 500_000, 2_000.0),  # USD 0.02 + 0.02 = 0.04
        _row("c1", 3_000_000, 500_000, 4_000.0),  # USD 0.06 + 0.02 = 0.08
    ]
    (cost,) = cost_per_incident(rows)
    assert cost.config_hash == "c1"
    assert cost.n == 2
    assert cost.mean_tokens_in == pytest.approx(2_000_000.0)
    assert cost.median_tokens_out == pytest.approx(500_000.0)
    # euros: (0.04 + 0.08)/2 = 0.06 USD mean -> /1.1225 EUR
    assert cost.mean_eur == pytest.approx(round((0.06 / USD_PER_EUR), 6))
    assert cost.mean_seconds == pytest.approx(3.0)  # (2 + 4)/2 s
    assert cost.median_seconds == pytest.approx(3.0)


def test_rejected_calls_are_included_via_row_totals() -> None:
    # A row whose tokens include a rejected attempt's tokens is costed like any other: the row
    # totals already sum every call (results.py), so there is nothing to exclude here.
    rows = [_row("c5", 2_000_000, 250_000, 1_500.0)]
    (cost,) = cost_per_incident(rows)
    assert cost.mean_eur == pytest.approx(round(row_eur(2_000_000, 250_000), 6))


def test_two_conditions_are_sorted_and_separate() -> None:
    rows = [_row("cB", 10, 10, 1.0), _row("cA", 20, 20, 2.0)]
    costs = cost_per_incident(rows)
    assert [c.config_hash for c in costs] == ["cA", "cB"]  # sorted by hash


def test_csv_header_carries_the_price_date(tmp_path: Path) -> None:
    path = tmp_path / "cost_per_incident.csv"
    write_cost_csv(cost_per_incident([_row("c1", 100, 50, 10.0)]), path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("#") and PRICE_DATE in lines[0]  # price date in the header
    assert lines[1].startswith("config_hash,")  # column header
    assert lines[2].startswith("c1,")  # one data row


def test_header_only_csv_when_no_rows(tmp_path: Path) -> None:
    path = tmp_path / "cost_per_incident.csv"
    write_cost_csv([], path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert PRICE_DATE in lines[0]
    assert lines[1].startswith("config_hash,")
    assert len(lines) == 2  # comment + header, no data
