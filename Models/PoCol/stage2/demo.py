"""Runnable demonstration of the Stage-2A PoCol scientific core.

    python -m Models.PoCol.stage2.demo

Runs a multi-round confirmatory simulation (real nonce search) and the matched
CONTROL vs POCOL_IDLE energy experiment, and prints the canonical A1 baseline
separately (never conflating a demo config with A1).
"""
from __future__ import annotations

from collections import Counter

from .config import Stage2Config, a1_continuous_control_kwh, A1_BASELINE_KWH
from .simulator import run_simulation
from .energy_experiment import run_energy_experiment
from .search import SUCCESS_MODEL, WORK_PRIMITIVE


def main() -> None:
    print("PoCol Stage-2A scientific core")
    print(f"  success model          : {SUCCESS_MODEL}")
    print(f"  per-nonce work primitive: {WORK_PRIMITIVE}")

    # canonical A1 baseline (NEVER a demo config).
    print(f"  canonical A1 baseline  : 141 miners x 21.5 W x 10000 s = "
          f"{a1_continuous_control_kwh(Stage2Config()):.9f} kWh "
          f"(target {A1_BASELINE_KWH})")

    # multi-round confirmatory simulation with the real search core.
    cfg = Stage2Config(num_miners=12, horizon_T=400.0, reserve_fraction=0.25,
                       nonce_domain_size=1200, batch_size=50)
    run = run_simulation(cfg)
    log_kinds = [o.kind for o in run.log]
    print("  --- confirmatory multi-round run ---")
    print(f"  rounds executed        : {run.round_seq}")
    print(f"  rounds accepted        : {log_kinds.count('accepted_block')}")
    print(f"  residency reconciles   : {run.residency_reconciles(run.run_end_time)}")
    print(f"  queue terminal states  : {dict(Counter(r.queue_status for r in run.event_queue.queued_event_registry.values()))}")

    # matched-control idle-policy energy experiment.
    res = run_energy_experiment(Stage2Config(nonce_domain_size=800, difficulty=1000),
                                n_miners=8)
    print("  --- matched CONTROL vs POCOL_IDLE energy experiment ---")
    print(f"  winner / winning nonce : {res.winner} / {res.winning_nonce}")
    print(f"  round end (s)          : {res.round_end:.4f}")
    print(f"  miners idling early    : {res.n_idlers}/{len(res.rows)}")
    print(f"  E_control (J)          : {res.total_control_j:.4f}")
    print(f"  E_pocol_idle (J)       : {res.total_idle_j:.4f}")
    print(f"  idle-policy saving (J) : {res.saving_j:.4f}")
    print(f"  max abs residual (J)   : {res.max_abs_residual_j:.3e}")
    zero = run_energy_experiment(Stage2Config(nonce_domain_size=800), n_miners=8,
                                 P_idle=Stage2Config().P_hash)
    print(f"  saving when P_idle=P_active : {zero.saving_j:.4f} (must be 0)")


if __name__ == "__main__":  # pragma: no cover
    main()
