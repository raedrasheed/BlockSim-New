"""Runnable demonstration of the Stage-2 PoCol core over the mandatory execution path.

    python -m Models.PoCol.stage2.demo

Runs a multi-round confirmatory simulation and prints the round count, the idle-policy
energy vs the A1 continuous-participation control, and the residency reconciliation.
"""
from __future__ import annotations

from collections import Counter

from .config import Stage2Config, a1_continuous_control_kwh
from .simulator import run_simulation


def main() -> None:
    cfg = Stage2Config(num_miners=20, horizon_T=1000.0, reserve_fraction=0.25)
    run = run_simulation(cfg)
    E = run.total_energy_kwh()
    A1 = a1_continuous_control_kwh(cfg)
    log_kinds = [o.kind for o in run.log]
    print("PoCol Stage-2 core — confirmatory run")
    print(f"  config                 : {cfg.num_miners} miners, T={cfg.horizon_T}s, "
          f"reserve_fraction={cfg.reserve_fraction}")
    print(f"  rounds executed        : {run.round_seq}")
    print(f"  rounds accepted        : {log_kinds.count('accepted_block')}")
    print(f"  loop result            : {run.loop_result.kind}")
    print(f"  residency reconciles   : {run.residency_reconciles(run.run_end_time)}")
    print(f"  E_total (idle policy)  : {E:.8f} kWh")
    print(f"  A1 continuous control  : {A1:.8f} kWh")
    print(f"  idle-policy saving     : {100.0 * (A1 - E) / A1:.2f} %")
    print(f"  driver_request states  : {dict(Counter(d.status for d in run.driver_request_registry.values()))}")
    print(f"  queue states at end    : {dict(Counter(r.queue_status for r in run.event_queue.queued_event_registry.values()))}")


if __name__ == "__main__":  # pragma: no cover
    main()
