"""Experiment: communication energy analysis.

Answers Reviewer 2.F: the communication-energy model is now exercised and
analyzed. We vary transaction rate, block size, and peer degree (connectivity),
count block/transaction messages explicitly, and compare communication energy
against consensus (computation) energy for both PoW and PoS.

Outputs:
  results/data/communication_energy_raw.csv
  results/data/communication_energy_summary.csv
"""

from _common import write_csv, N_SEEDS, SEED_BASE
from Models.Energy.scenarios import (run_pow_scenario, run_pos_scenario,
                                      make_seeds, summarize)
from Models.Energy.energy_models import CommunicationEnergyModel

HORIZON_S = 86400.0
NUM_NODES = 500
PEER_DEGREES = [4, 8, 16]
TX_RATES_HZ = [1, 10, 100]          # transactions per second
BLOCK_SIZES_BYTES = [0.5e6, 1.0e6, 2.0e6]

# Per-message + per-byte energy (Joules). Order-of-magnitude radio/NIC values.
E_TX_MSG = 0.10
E_RX_MSG = 0.05
E_TX_BYTE = 2.0e-6
E_RX_BYTE = 1.0e-6


def _comm_energy_kwh(num_blocks, num_tx, peer_degree, block_size, tx_size=512):
    cm = CommunicationEnergyModel(tx_energy_per_message_j=E_TX_MSG,
                                  rx_energy_per_message_j=E_RX_MSG,
                                  tx_energy_per_byte_j=E_TX_BYTE,
                                  rx_energy_per_byte_j=E_RX_BYTE)
    cm.account_broadcast(num_messages=int(num_blocks), num_nodes=NUM_NODES,
                         peer_degree=peer_degree, kind="block", size_bytes=block_size)
    cm.account_broadcast(num_messages=int(num_tx), num_nodes=NUM_NODES,
                         peer_degree=peer_degree, kind="tx", size_bytes=tx_size)
    return cm.total_energy_kwh(), cm


def main():
    seeds = make_seeds(N_SEEDS, SEED_BASE)
    raw_rows, summary_rows = [], []

    for pd in PEER_DEGREES:
        for tx_rate in TX_RATES_HZ:
            for bsize in BLOCK_SIZES_BYTES:
                comm_e, comp_e, ratios, msg_counts = [], [], [], []
                for s in seeds:
                    pw = run_pow_scenario(seed=s, miner_count=NUM_NODES, horizon_s=HORIZON_S)
                    num_blocks = pw.num_blocks
                    num_tx = tx_rate * HORIZON_S
                    ce, cm = _comm_energy_kwh(num_blocks, num_tx, pd, bsize)
                    comm_e.append(ce)
                    comp_e.append(pw.network_energy_kwh)
                    ratios.append(ce / pw.network_energy_kwh if pw.network_energy_kwh else 0.0)
                    msg_counts.append(cm.total_messages)
                    raw_rows.append(dict(peer_degree=pd, tx_rate_hz=tx_rate,
                                         block_size_mb=bsize / 1e6, seed=s,
                                         comm_energy_kwh=ce,
                                         pow_compute_energy_kwh=pw.network_energy_kwh,
                                         comm_to_compute_ratio=ratios[-1],
                                         total_messages=cm.total_messages))
                su = summarize(comm_e)
                summary_rows.append(dict(peer_degree=pd, tx_rate_hz=tx_rate,
                                         block_size_mb=bsize / 1e6,
                                         comm_energy_mean_kwh=su["mean"],
                                         comm_energy_ci95_kwh=su["ci95_halfwidth"],
                                         pow_compute_mean_kwh=summarize(comp_e)["mean"],
                                         comm_to_compute_ratio=summarize(ratios)["mean"],
                                         mean_total_messages=summarize(msg_counts)["mean"],
                                         n_seeds=su["n"]))
        print(f"[Comm peer_degree={pd}] swept tx-rate x block-size grid")

    write_csv("communication_energy_raw.csv", raw_rows,
              ["peer_degree", "tx_rate_hz", "block_size_mb", "seed",
               "comm_energy_kwh", "pow_compute_energy_kwh",
               "comm_to_compute_ratio", "total_messages"])
    write_csv("communication_energy_summary.csv", summary_rows,
              ["peer_degree", "tx_rate_hz", "block_size_mb",
               "comm_energy_mean_kwh", "comm_energy_ci95_kwh",
               "pow_compute_mean_kwh", "comm_to_compute_ratio",
               "mean_total_messages", "n_seeds"])
    return summary_rows


if __name__ == "__main__":
    main()
