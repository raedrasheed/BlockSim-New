# Stage 5B1 — Coordination Instrumentation

**Blocker 4 (Stage 5A):** coordination was not instrumented, so protocol overhead
was invisible and could be silently assumed to be zero. Stage 5B1 separates three
categories and never conflates them.

## 1. Three categories, kept distinct

| Category | What it is | How it is reported |
|----------|-----------|--------------------|
| **Simulated messages** | Events the engine actually generates (block propagation to the other miners) | `coord_block_propagation_message_count`, `coord_block_propagation_bytes`, `coord_simulated_message_count/bytes` |
| **Abstract protocol operations** | Operations the *protocol* requires but the simulator does **not** execute (per-block common-template agreement, transaction reconciliation) | `abstract_template_agreement_operations`, `abstract_transaction_reconciliation_operations` (counts only) |
| **Coordination energy** | Energy attributable to coordination | `coordination_energy_kwh = 0.0` (explicit idealized lower bound); `unimplemented_agreement_energy_kwh = null` |

## 2. The critical honesty rule

`unimplemented_agreement_energy_kwh` is **`null`, not `0`**. Zero would assert
"coordination is free"; null asserts "we did not measure it". The idealized model
carries an explicit **lower bound** of 0 (`coordination_energy_lower_bound_kwh`),
so any downstream energy comparison is transparently a *lower bound* on real
PoCol cost, never a claim of equivalence.

## 3. Simulated vs abstract — worked example (B3/C1, N=100)

- Block propagation: each accepted block is sent to `n−1` miners → `msgs =
  (active − 1)` messages, `msgs · 1 MB` bytes. Reconciled exactly: bytes =
  messages × 1 000 000 (check `E1`).
- Abstract agreement: one per accepted block for common-template scenarios;
  **zero** for B0 (independent templates need no agreement) — check `E5`.
- Template refresh: incremented on every exhausted generation; equals
  `exhausted_rounds` exactly (check `E2`).

## 4. Reconciliations (category E, `STAGE_05B1_VALIDATION_REPORT.md`)

| Check | Statement | Result |
|-------|-----------|--------|
| E1 | propagation bytes = messages × 1 MB | pass |
| E2 | template refreshes = exhausted rounds | pass |
| E3 | unimplemented agreement energy is `null` | pass |
| E4 | coordination lower bound and energy both explicit 0 | pass |
| E5 | common-template has agreement ops; B0 has none | pass |
| E6 | agreement operations = accepted blocks (events) | pass |

## 5. Consequence for the thesis

The thesis may report simulated coordination volume (messages, bytes) as a
measured quantity, and must report the agreement/reconciliation cost as an
**unquantified overhead (null)** bounded below by zero — never as evidence that
PoCol coordination is negligible.
