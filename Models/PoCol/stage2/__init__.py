"""Stage-2 executable PoCol core simulator.

Implemented from the FROZEN Stage-1 normative baseline
(8c9902e57c0d6557329bc742e39a50ed31b86170).  The algorithm is **PoCol**; the
energy-saving mechanism is **the idle policy within PoCol** (low-power residency,
never nonce partitioning).  No dynamic difficulty is used in the confirmatory core.
"""
from __future__ import annotations

from .config import (Stage2Config, A1_BASELINE_KWH, JOULES_PER_KWH,
                     a1_continuous_control_kwh)
from .events import (EventRef, EventQueue, Outcome, ScheduleEvent, CancelQueuedEvent,
                     Driver, OrdinaryDispatch, PostEpilogue, TerminalRotation,
                     ordinary_dispatch_origin, driver_kind_may_seat,
                     next_representable_simulation_time, DESCRIPTORS,
                     MICROPHASE_ORDINAL)
from .context import (RunContext, RoundContext, BootstrapRequest, DriverRequest,
                      MinerRecord, EvaluationRecord, EXACT_ROUND, NEXT_AVAILABLE_ROUND,
                      RUN_LEVEL, MINER_STATES, DRIVER_REQUEST_STATUSES)
from .driver import (SeatMinerRegister, SeatReserveActivate, SeatNextRoundBootstrap,
                     SeatPendingDriverRequests, SeatDriverEventTransaction, scope_admits)
from .search import (Template, MinerSearchState, make_template, partition_domain,
                     sha256_int, target_for_difficulty, success_probability,
                     SUCCESS_MODEL, WORK_PRIMITIVE)
from .simulator import (RunInitialise, RunEventLoopToHorizon, ProcessEventTime,
                        RoundAbort, FinalizeSimulationRun, FinalizeSimulationRunNoRound,
                        FinalizeSimulationRunPartial, run_simulation)
from .energy_experiment import (run_energy_experiment, EnergyExperimentResult,
                                MinerEnergyRow)
from .adapter import (run_pocol_stage2, stage2config_from_blocksim, results_schema,
                      RESULT_SCHEMA_VERSION)

__all__ = [
    "Stage2Config", "A1_BASELINE_KWH", "JOULES_PER_KWH", "a1_continuous_control_kwh",
    "EventRef", "EventQueue", "Outcome", "ScheduleEvent", "CancelQueuedEvent",
    "Driver", "OrdinaryDispatch", "PostEpilogue", "TerminalRotation",
    "ordinary_dispatch_origin", "driver_kind_may_seat",
    "next_representable_simulation_time", "DESCRIPTORS", "MICROPHASE_ORDINAL",
    "RunContext", "RoundContext", "BootstrapRequest", "DriverRequest", "MinerRecord",
    "EvaluationRecord", "EXACT_ROUND", "NEXT_AVAILABLE_ROUND", "RUN_LEVEL", "MINER_STATES",
    "DRIVER_REQUEST_STATUSES",
    "SeatMinerRegister", "SeatReserveActivate", "SeatNextRoundBootstrap",
    "SeatPendingDriverRequests", "scope_admits",
    "RunInitialise", "RunEventLoopToHorizon", "ProcessEventTime", "RoundAbort",
    "FinalizeSimulationRun", "FinalizeSimulationRunNoRound", "FinalizeSimulationRunPartial",
    "run_simulation",
    "SeatDriverEventTransaction",
    "Template", "MinerSearchState", "make_template", "partition_domain", "sha256_int",
    "target_for_difficulty", "success_probability", "SUCCESS_MODEL", "WORK_PRIMITIVE",
    "run_energy_experiment", "EnergyExperimentResult", "MinerEnergyRow",
    "run_pocol_stage2", "stage2config_from_blocksim", "results_schema",
    "RESULT_SCHEMA_VERSION",
]
