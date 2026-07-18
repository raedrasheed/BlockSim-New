"""Statistics (bootstrap CIs, paired diffs, pre-registered TOST) -- reuses the
tested machinery from experiments/continuous_distributed_effort/statistics.py."""
from experiments.continuous_distributed_effort.statistics import (  # noqa: F401
    summarize, paired_diff, tost_equivalence,
)

# Pre-registered BEFORE inspecting results (same rule as prior experiments):
# PoCol vs independent-header PoW energy equivalence margin = 1% of control mean.
POCOL_VS_IND_MARGIN_REL = 0.01
