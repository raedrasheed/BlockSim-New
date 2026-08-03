"""Runnable demonstration of the Stage-2B target-coupled PoCol scientific core.

    python -m Models.PoCol.stage2.demo

Runs a multi-round confirmatory simulation (real target-coupled nonce search) and the
CONSTRUCTED matched CONTROL-vs-POCOL_IDLE identity experiment, and prints the canonical A1
accounting reference separately (never conflating a demo config with A1, and never
reporting the run vs A1 as a general PoCol saving).
"""
from __future__ import annotations

from collections import Counter

from .config import Stage2Config, a1_continuous_control_kwh, A1_BASELINE_KWH
from .simulator import run_simulation
from .energy_experiment import run_energy_experiment
from .search import SUCCESS_MODEL, WORK_PRIMITIVE, target_for_difficulty, success_probability


def main() -> None:
    print("PoCol Stage-2B target-coupled scientific core")
    print(f"  success model           : {SUCCESS_MODEL}")
    print(f"  per-nonce work primitive: {WORK_PRIMITIVE}")
    cfg0 = Stage2Config()
    tgt = target_for_difficulty(cfg0.difficulty)
    print(f"  difficulty / p          : {cfg0.difficulty} / {success_probability(tgt):.3e}")

    # canonical A1 accounting reference (NEVER a demo config; NOT a matched saving basis).
    print(f"  canonical A1 reference  : 141 miners x 21.5 W x 10000 s = "
          f"{a1_continuous_control_kwh(cfg0):.9f} kWh (target {A1_BASELINE_KWH})")

    # multi-round confirmatory simulation with the real target-coupled search core.
    cfg = Stage2Config(num_miners=12, horizon_T=400.0, reserve_fraction=0.25,
                       nonce_domain_size=1200, batch_size=50)
    run = run_simulation(cfg)
    log_kinds = [o.kind for o in run.log]
    print("  --- confirmatory multi-round run ---")
    print(f"  rounds executed         : {run.round_seq}")
    print(f"  rounds accepted (block) : {log_kinds.count('accepted_block')}")
    print(f"  rounds no-block/aborted : {log_kinds.count('round_aborted')}")
    print(f"  evaluation-ledger entries: {len(run.evaluation_ledger)}")
    print(f"  residency reconciles    : {run.residency_reconciles(run.run_end_time)}")
    print(f"  queue terminal states   : {dict(Counter(r.queue_status for r in run.event_queue.queued_event_registry.values()))}")

    # CONSTRUCTED matched identity-validation experiment (NOT a general PoCol saving).
    res = run_energy_experiment(Stage2Config(nonce_domain_size=2400), n_miners=8)
    print("  --- constructed matched CONTROL vs POCOL_IDLE identity experiment ---")
    print(f"  scenario                : {res.scenario} (seed {res.seed})")
    print(f"  winner / winning nonce  : {res.winner} / {res.winning_nonce}")
    print(f"  round end (s)           : {res.round_end:.4f}")
    print(f"  miners idling early     : {res.n_idlers}/{len(res.rows)}")
    print(f"  E_control (J)           : {res.total_control_j:.4f}")
    print(f"  E_pocol_idle (J)        : {res.total_idle_j:.4f}")
    print(f"  scenario saving (J)     : {res.saving_j:.4f}  [constructed scenario only]")
    print(f"  max abs identity residual (J): {res.max_abs_residual_j:.3e}")
    zero = run_energy_experiment(Stage2Config(nonce_domain_size=2400), n_miners=8,
                                 P_idle=Stage2Config().P_hash)
    print(f"  saving when P_idle=P_active : {zero.saving_j:.4f} (must be 0)")


if __name__ == "__main__":  # pragma: no cover
    main()
