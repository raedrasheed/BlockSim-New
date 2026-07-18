"""Run ONE corrected-simulator scenario with the PoCol equal-share idle
extension toggled ON or OFF (fresh process; wraps experiments/run_scenario.run).

The extension (Models/PoCol: PoCol_IdleAfterRange) runs PoCol in fixed slots of
Binterval seconds; each miner works only on its own disjoint share of the nonce
domain, and when the round closes every miner powers down to 0 W until the next
slot boundary. Energy saving emerges from genuinely shorter ACTIVE time.

Restart policies (PoCol_RestartPolicy):
  slot      -- wait for the next slot boundary, miners IDLE at 0 W in between
  immediate -- next round starts AT the close time (like PoW): faster blocks,
               miners never idle, so the energy saving disappears

CLI:  python experiments/run_scenario_idle.py <PoW|PoCol> <n> <seed> <mode>
      mode: off | slot | immediate   (legacy: 0 = off, 1 = slot)
"""
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_with_idle(protocol, n, seed, mode="off"):
    mode = {"0": "off", "1": "slot"}.get(str(mode), str(mode)).lower()
    if mode not in ("off", "slot", "immediate"):
        raise ValueError(f"unknown mode {mode!r} (off|slot|immediate)")

    from InputsConfig import InputsConfig as p
    p.PoCol_IdleAfterRange = mode != "off"       # opt-in flag (default OFF)
    p.PoCol_RestartPolicy = "immediate" if mode == "immediate" else "slot"

    from Models.PoCol.Consensus import Consensus
    Consensus.next_slot_start = 0.0              # fresh-run reset

    from experiments.run_scenario import run
    rec = run(protocol, n, seed)
    rec["idle_after_range"] = p.PoCol_IdleAfterRange
    rec["restart_policy"] = p.PoCol_RestartPolicy
    rec["mode"] = mode

    # per-miner fairness + idle accounting
    active = [getattr(nd, "cumulative_active_time", 0.0) for nd in p.NODES]
    idle_t = [getattr(nd, "pocol_idle_time_s", 0.0) for nd in p.NODES]
    energy = [getattr(nd, "energy_kwh", 0.0) for nd in p.NODES]
    rec["idle_miner_seconds"] = sum(idle_t)
    rec["pct_time_active"] = 100.0 * sum(active) / (n * p.simTime) if p.simTime else float("nan")
    rec["per_miner_energy_kwh_min"] = min(energy) if energy else float("nan")
    rec["per_miner_energy_kwh_max"] = max(energy) if energy else float("nan")
    return rec


if __name__ == "__main__":
    proto = sys.argv[1]; n = int(sys.argv[2]); seed = int(sys.argv[3])
    mode = sys.argv[4] if len(sys.argv) > 4 else "off"
    print(json.dumps(run_with_idle(proto, n, seed, mode)))
