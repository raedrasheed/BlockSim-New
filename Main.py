# Main.py (fixed + PoCol-ready)

from datetime import datetime
from InputsConfig import InputsConfig as p
from Event import Event, Queue
from Scheduler import Scheduler

import importlib

# Base Statistics (models 0/1/2/3)
from Statistics import Statistics as BaseStatistics


# --------------------------- Model-specific imports ---------------------------

# Keep these at module-scope (NOT inside main) to avoid UnboundLocalError issues.
# They may remain None depending on model/technique and will be loaded safely at runtime.
LT = None
FT = None

# Default binding for non-AppendableBlock models
Statistics = BaseStatistics


def _tx_module_path():
    """Return the transaction module path based on the selected model."""
    if p.model == 2:
        return "Models.Ethereum.Transaction"
    if p.model == 4:
        return "Models.AppendableBlock.Transaction"
    # models 0/1/3 share the common tx module in BlockSim
    return "Models.Transaction"


def _create_pending_transactions():
    """
    Create pending transactions using the chosen technique.
    This avoids importing/assigning LT/FT inside main() (prevents UnboundLocalError).
    """
    global LT, FT

    if not getattr(p, "hasTrans", False):
        return

    tech = getattr(p, "Ttechnique", "Light")
    mod_path = _tx_module_path()

    # Load module dynamically only if needed (safe, deterministic).
    tx_mod = importlib.import_module(mod_path)

    if tech == "Light":
        if LT is None:
            # get LightTransaction class from the module
            LT = getattr(tx_mod, "LightTransaction")
        # LT.create_transactions(0, True)
        LT.create_transactions()


    elif tech == "Full":
        if FT is None:
            FT = getattr(tx_mod, "FullTransaction")
        FT.create_transactions()


# 4 : AppendableBlock (legacy/optional)
if p.model == 4:
    from Models.AppendableBlock.BlockCommit import BlockCommit
    from Models.Consensus import Consensus
    from Models.AppendableBlock.Transaction import FullTransaction as FT  # model-specific FT
    from Models.AppendableBlock.Node import Node
    from Models.Incentives import Incentives
    from Models.AppendableBlock.Statistics import Statistics as ABStatistics
    from Models.AppendableBlock.Verification import Verification

    Statistics = ABStatistics  # override

# 3 : PoCol (your new model)
elif p.model == 3:
    from Models.PoCol.BlockCommit import BlockCommit
    from Models.PoCol.Consensus import Consensus
    from Models.Transaction import LightTransaction as LT, FullTransaction as FT
    from Models.PoCol.Node import Node
    from Models.Incentives import Incentives

# 2 : Ethereum
elif p.model == 2:
    from Models.Ethereum.BlockCommit import BlockCommit
    from Models.Ethereum.Consensus import Consensus
    from Models.Ethereum.Transaction import LightTransaction as LT, FullTransaction as FT
    from Models.Ethereum.Node import Node
    from Models.Ethereum.Incentives import Incentives

# 1 : Bitcoin
elif p.model == 1:
    from Models.Bitcoin.BlockCommit import BlockCommit
    from Models.Bitcoin.Consensus import Consensus
    from Models.Transaction import LightTransaction as LT, FullTransaction as FT
    from Models.Bitcoin.Node import Node
    from Models.Incentives import Incentives

# 0 : Base
elif p.model == 0:
    from Models.BlockCommit import BlockCommit
    from Models.Consensus import Consensus
    from Models.Transaction import LightTransaction as LT, FullTransaction as FT
    from Models.Node import Node
    from Models.Incentives import Incentives

else:
    raise ValueError(f"Unsupported model={p.model}. Expected 0,1,2,3,4")


# --------------------------- Start Simulation ---------------------------

def main():
    for run_idx in range(p.Runs):
        clock = 0

        # 1) create pending transactions (safe)
        _create_pending_transactions()

        # 2) genesis + initial events
        Node.generate_gensis_block()
        BlockCommit.generate_initial_events()

        # 3) run event loop
        while not Queue.isEmpty() and clock <= p.simTime:
            next_event = Queue.get_next_event()
            clock = next_event.time
            BlockCommit.handle_event(next_event)
            Queue.remove_event(next_event)

        # 3b) Stage 2: flush any still-open ACTIVE mining interval up to the
        #     simulation cutoff (idempotent; never accounts beyond simTime).
        #     Thesis energy path only (PoW=model 1, PoCol=model 3).
        if p.model in (1, 3) and hasattr(Node, "finalize_energy"):
            Node.finalize_energy(p.simTime)

        # 4) AppendableBlock-only post-processing
        if p.model == 4:
            BlockCommit.process_gateway_transaction_pools()
            if run_idx == 0 and getattr(p, "VerifyImplemetation", False):
                Verification.perform_checks()

        # 5) forks + rewards + statistics
        Consensus.fork_resolution()
        Incentives.distribute_rewards()
        Statistics.calculate()

        # 6) output + reset (handle different signatures cleanly)
        if p.model == 4:
            # AppendableBlock statistics usually use (run_idx, True)
            Statistics.print_to_excel(run_idx, True)
            Statistics.reset()
        else:
            # Standard models: print to excel file name
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Model ID -> human-friendly name
            MODEL_NAME = {
                0: "Base",
                1: "Bitcoin",
                2: "Ethereum",
                3: "PoCol",
                4: "AppendableBlock",
            }

            model_name = MODEL_NAME.get(p.model, f"Model{p.model}")

            fname = model_name + "_" + str(ts) + "_(Allverify)1day_{0}M_{1}K_run{2}.xlsx".format(
                p.Bsize / 1000000, p.Tn / 1000, run_idx
            )
            Statistics.print_to_excel(fname)

            # reset for next run
            if hasattr(Statistics, "reset"):
                Statistics.reset()
            if hasattr(Node, "resetState"):
                Node.resetState()

        # Some versions include reset2 (profit results); call only if exists
        if hasattr(Statistics, "reset2"):
            Statistics.reset2()


# --------------------------- Run Main ---------------------------

if __name__ == '__main__':
    main()
