from InputsConfig import InputsConfig as p
from Models.Consensus import Consensus as c
import pandas as pd

PROFIT_COLS = 10


class Statistics:
    # ---- constants ----
    _PROFIT_COLS = PROFIT_COLS
    _ENERGYLOG_COLS = ["t", "miner_id", "dt", "hashes", "energy_kwh", "co2_kg", "reason", "parent_id", "block_id"]

    def __init__(self):
        # profits as instance variable (not shared)
        self.profits = [[0 for _ in range(PROFIT_COLS)]
                        for _ in range(p.Runs * len(p.NODES))]

    # ---- block stats ----
    totalBlocks = 0
    mainBlocks = 0
    totalUncles = 0
    uncleBlocks = 0
    staleBlocks = 0
    uncleRate = 0.0
    staleRate = 0.0

    # totals
    totalAttempts = 0.0
    totalEnergy_kWh = 0.0
    totalCO2_kg = 0.0

    blocksResults = []
    chain = []

    profits = [[0 for _ in range(PROFIT_COLS)] for _ in range(p.Runs * len(p.NODES))]
    index = 0

    # EnergyLog rows
    energyLog = []
    EnergyLog = energyLog

    # Dedup guard
    _energylog_seen = set()

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _safe_pct(n, d):
        return round((n / d) * 100, 2) if d else 0.0

    @staticmethod
    def _ensure_alias():
        if not hasattr(Statistics, "energyLog") or Statistics.energyLog is None:
            Statistics.energyLog = []
        Statistics.EnergyLog = Statistics.energyLog

    @staticmethod
    def _find_node(miner_id):
        try:
            for n in p.NODES:
                if getattr(n, "id", None) == miner_id:
                    return n
        except Exception:
            pass
        return None

    @staticmethod
    def _net_hashrate_hps():
        for name in ("NetworkHashRate_Hps", "NetworkHashRateHPS", "NetworkHashRate", "NhashRate"):
            if hasattr(p, name) and getattr(p, name) is not None:
                try:
                    return float(getattr(p, name))
                except Exception:
                    return 0.0
        return 0.0

    @staticmethod
    def _total_hashpower_units():
        try:
            total = 0.0
            for n in p.NODES:
                total += float(getattr(n, "hashPower", 1.0) or 1.0)
            return total if total > 0.0 else float(max(1, len(p.NODES)))
        except Exception:
            return 1.0

    @staticmethod
    def _eff_j_per_hash():
        # MinerEfficiency_J_per_TH (J/TH) -> J/hash by / 1e12
        for name in ("MinerEfficiency_J_per_TH", "MinerEfficiency", "Efficiency_J_per_TH", "J_per_TH"):
            if hasattr(p, name) and getattr(p, name) is not None:
                try:
                    j_per_th = float(getattr(p, name))
                    return j_per_th / 1e12
                except Exception:
                    return 0.0
        return 0.0

    # -------------------------
    # Energy logging
    # -------------------------
    @staticmethod
    def log_energy(t, miner_id, dt, hashes, energy_kwh, co2_kg, reason="", parent_id=None, block_id=None):
        """
        Append a single per-miner energy row.

        FIX:
        - If hashes == 0 (or None) but dt > 0, backfill hashes using:
            hashes = (NetworkHashRate_Hps * miner_fraction) * dt
          where miner_fraction is based on hashPower / sum(hashPower).
        - If NetworkHashRate_Hps is missing, infer hashrate from energy+efficiency:
            power_w = (energy_kwh * 3.6e6) / dt
            hashrate = power_w / (MinerEfficiency_J_per_TH / 1e12)
        """
        Statistics._ensure_alias()

        # normalize numeric fields
        try:
            t = float(t or 0.0)
        except Exception:
            t = 0.0
        try:
            dt = float(dt or 0.0)
        except Exception:
            dt = 0.0
        try:
            hashes = float(hashes or 0.0)
        except Exception:
            hashes = 0.0
        try:
            energy_kwh = float(energy_kwh or 0.0)
        except Exception:
            energy_kwh = 0.0
        try:
            co2_kg = float(co2_kg or 0.0)
        except Exception:
            co2_kg = 0.0

        # ---- BACKFILL hashes if missing ----
        if hashes == 0.0 and dt > 0.0:
            net = Statistics._net_hashrate_hps()
            if net > 0.0:
                total_hp = Statistics._total_hashpower_units()
                node = Statistics._find_node(miner_id)
                try:
                    hp = float(getattr(node, "hashPower", 1.0) or 1.0) if node is not None else 1.0
                except Exception:
                    hp = 1.0
                frac = hp / total_hp if total_hp > 0 else 1.0 / float(max(1, len(p.NODES)))
                hashes = (net * frac) * dt
            else:
                eff = Statistics._eff_j_per_hash()
                if eff > 0.0 and energy_kwh > 0.0:
                    power_w = (energy_kwh * 3_600_000.0) / dt
                    hashrate = power_w / eff
                    hashes = hashrate * dt

        row = {
            "t": t,
            "miner_id": miner_id,
            "dt": dt,
            "hashes": hashes,
            "energy_kwh": energy_kwh,
            "co2_kg": co2_kg,
            "reason": str(reason or ""),
            "parent_id": parent_id,
            "block_id": block_id,
        }

        key = tuple(row.get(k) for k in Statistics._ENERGYLOG_COLS)
        if key in Statistics._energylog_seen:
            return
        Statistics._energylog_seen.add(key)

        Statistics.energyLog.append(row)
        Statistics._ensure_alias()

    # -------------------------
    # Main calculation
    # -------------------------
    @staticmethod
    def calculate():
        Statistics.global_chain()
        Statistics.blocks_results()
        Statistics.profit_results()

    @staticmethod
    def blocks_results():
        trans = 0

        chain_len = len(getattr(c, "global_chain", []))
        Statistics.mainBlocks = max(chain_len - 1, 0)
        Statistics.staleBlocks = max(Statistics.totalBlocks - Statistics.mainBlocks, 0)

        # tx count + uncle count (Ethereum only)
        Statistics.uncleBlocks = 0
        for b in getattr(c, "global_chain", []):
            if hasattr(b, "transactions") and b.transactions is not None:
                trans += len(b.transactions)
            if p.model == 2 and hasattr(b, "uncles") and b.uncles is not None:
                Statistics.uncleBlocks += len(b.uncles)

        Statistics.totalUncles = Statistics.uncleBlocks if p.model == 2 else 0

        Statistics.staleRate = Statistics._safe_pct(Statistics.staleBlocks, Statistics.totalBlocks)
        Statistics.uncleRate = Statistics._safe_pct(Statistics.uncleBlocks, Statistics.totalBlocks) if p.model == 2 else 0.0

        # ---- energy totals from nodes ----
        # attempts_hashes is preferred; fallback to 'hashes'
        Statistics.totalAttempts = 0.0
        for n in p.NODES:
            Statistics.totalAttempts += float(getattr(n, "attempts_hashes", getattr(n, "hashes", 0.0)) or 0.0)

        Statistics.totalEnergy_kWh = sum(float(getattr(n, "energy_kwh", 0.0) or 0.0) for n in p.NODES)
        Statistics.totalCO2_kg = sum(float(getattr(n, "co2_kg", 0.0) or 0.0) for n in p.NODES)

        Statistics.blocksResults.append([
            Statistics.totalBlocks,
            Statistics.mainBlocks,
            Statistics.uncleBlocks,
            Statistics.uncleRate,
            Statistics.staleBlocks,
            Statistics.staleRate,
            trans,
            Statistics.totalAttempts,
            Statistics.totalEnergy_kWh,
            Statistics.totalCO2_kg
        ])

    @staticmethod
    def profit_results():
        main_blocks = Statistics.mainBlocks

        for m in p.NODES:
            i = Statistics.index + m.id * p.Runs
            Statistics.profits[i][0] = m.id
            Statistics.profits[i][1] = getattr(m, "hashPower", "NA")
            Statistics.profits[i][2] = getattr(m, "blocks", 0)
            Statistics.profits[i][3] = Statistics._safe_pct(getattr(m, "blocks", 0), main_blocks)

            # Ethereum-only placeholders kept
            Statistics.profits[i][4] = getattr(m, "uncles", 0) if p.model == 2 else 0
            Statistics.profits[i][5] = 0.0

            Statistics.profits[i][6] = getattr(m, "balance", 0)

            # ---- energy columns ----
            Statistics.profits[i][7] = float(getattr(m, "attempts_hashes", getattr(m, "hashes", 0.0)) or 0.0)
            Statistics.profits[i][8] = float(getattr(m, "energy_kwh", 0.0) or 0.0)
            Statistics.profits[i][9] = float(getattr(m, "co2_kg", 0.0) or 0.0)

        Statistics.index += 1

    @staticmethod
    def global_chain():
        Statistics.chain = []
        for b in getattr(c, "global_chain", []):
            depth = getattr(b, "depth", None)
            bid = getattr(b, "id", None)
            prev = getattr(b, "previous", None)
            ts = getattr(b, "timestamp", None)
            miner = getattr(b, "miner", None)
            txs = getattr(b, "transactions", []) or []
            size = getattr(b, "size", getattr(b, "usedgas", None))
            Statistics.chain.append([depth, bid, prev, ts, miner, len(txs), size])

    @staticmethod
    def print_to_excel(fname):
        Statistics._ensure_alias()

        df1 = pd.DataFrame({
            "Model": [p.model],
            "Block Interval (s)": [p.Binterval],
            "Block Prop Delay (s)": [p.Bdelay],
            "No. Miners": [len(p.NODES)],
            "Simulation Time (s)": [p.simTime],
            "Network Hash Rate (H/s)": [getattr(p, "NetworkHashRate_Hps", "NA")],
            "MinerEfficiency (J/TH)": [getattr(p, "MinerEfficiency_J_per_TH", "NA")],
            "GridEF (kgCO2e/kWh)": [getattr(p, "GridEF_kgCO2e_per_kWh", "NA")]
        })

        sim_cols = [
            "Total Blocks", "Main Blocks", "Uncle blocks", "Uncle Rate",
            "Stale Blocks", "Stale Rate", "# transactions",
            "Total Attempts/Hashes", "Total Energy (kWh)", "Total CO2 (kgCO2e)"
        ]
        df2 = pd.DataFrame(Statistics.blocksResults, columns=sim_cols)

        profit_cols = [
            "Miner ID", "% Hash Power", "# Mined Blocks", "% of main blocks",
            "# Uncle Blocks", "% of uncles", "Profit",
            "Attempts/Hashes", "Energy (kWh)", "CO2 (kgCO2e)"
        ]
        df3 = pd.DataFrame(Statistics.profits, columns=profit_cols)

        df4 = pd.DataFrame(Statistics.chain, columns=[
            "Block Depth", "Block ID", "Previous Block", "Block Timestamp",
            "Miner ID", "# transactions", "Block Size/UsedGas"
        ])

        df5 = pd.DataFrame(Statistics.energyLog, columns=Statistics._ENERGYLOG_COLS)
        # remove exact duplicates (keep first)
        df5 = df5.drop_duplicates(subset=Statistics._ENERGYLOG_COLS, keep="first", ignore_index=True)

        with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
            df1.to_excel(writer, sheet_name="InputConfig", index=False)
            df2.to_excel(writer, sheet_name="SimOutput", index=False)
            df3.to_excel(writer, sheet_name="ProfitEnergy", index=False)
            df4.to_excel(writer, sheet_name="Chain", index=False)
            df5.to_excel(writer, sheet_name="EnergyLog", index=False)

    @staticmethod
    def reset():
        Statistics.totalBlocks = 0
        Statistics.mainBlocks = 0
        Statistics.totalUncles = 0
        Statistics.uncleBlocks = 0
        Statistics.staleBlocks = 0
        Statistics.uncleRate = 0.0
        Statistics.staleRate = 0.0
        Statistics.totalAttempts = 0.0
        Statistics.totalEnergy_kWh = 0.0
        Statistics.totalCO2_kg = 0.0

    @staticmethod
    def reset2():
        Statistics.blocksResults = []
        Statistics.chain = []
        Statistics.energyLog = []
        Statistics.EnergyLog = Statistics.energyLog
        Statistics._energylog_seen = set()
        Statistics.profits = [[0 for _ in range(Statistics._PROFIT_COLS)] for _ in range(p.Runs * len(p.NODES))]
        Statistics.index = 0
