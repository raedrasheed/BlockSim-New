"""Stage 8X-NR — traversal policies over the 32-bit nonce-value domain.

Time is counted in integer ticks (1 tick = one candidate evaluation per miner =
1/h seconds). A miner's traversal maps a tick interval to the multiset of
nonce32 values it evaluated, always expressible as f complete sweeps of the
domain plus one partial cyclic arc — no value is ever materialised.

Policies (brief section 9)
--------------------------
ZERO    zero-start sequential: nonce = tick position since last template start,
        beginning at 0. Deliberately synchronized worst-case control.
OFFSET  independently offset sequential: start_i ~ Uniform(0, 2^32-1) drawn once
        per run per miner; nonce = (start_i + t_abs) mod 2^32, advancing
        cyclically and continuously across template renewals.

Template renewal (brief section 22)
-----------------------------------
A miner exhausts the explicit 2^32 header-nonce domain every 2^32 ticks. It then
rolls its extranonce (new Merkle root, new template) and continues:
ZERO restarts at nonce 0 under the new template (counted as a nonce reset);
OFFSET continues cyclically (exhaustion counted, no positional reset).
Round boundaries also renew templates (new previous-block context) — under ZERO
this resets the nonce phase to 0; under OFFSET the phase is unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from experiments.stage8xnr.config.nr_config import S_NONCE

Arc = Tuple[int, int]


@dataclass
class TraversalWindow:
    """Exact description of one miner's evaluations over a tick window."""
    ticks: int                 # total evaluations in the window
    full_sweeps: int           # complete traversals of the 2^32 domain
    partial_arc: Arc           # remaining (start, length), length < 2^32

    @property
    def covers_domain(self) -> bool:
        return self.full_sweeps >= 1

    def coverage_arc(self) -> Arc:
        """The SET of values touched, as a single arc (length clamped to S)."""
        if self.covers_domain:
            return (0, S_NONCE)
        return self.partial_arc


def window(phase: int, ticks: int) -> TraversalWindow:
    """Evaluations of a miner whose nonce phase at window start is ``phase``.

    ``phase`` is the nonce32 value evaluated at the first tick of the window.
    """
    if ticks < 0:
        raise ValueError("ticks must be >= 0")
    full, rem = divmod(ticks, S_NONCE)
    return TraversalWindow(ticks=ticks, full_sweeps=full,
                           partial_arc=(phase % S_NONCE, rem))


def zero_start_phase() -> int:
    """ZERO policy: every template epoch (and round) starts at nonce 0."""
    return 0


def offset_phase(start: int, t_abs: int) -> int:
    """OFFSET policy: continuous cyclic position (start_i + absolute ticks)."""
    return (start + t_abs) % S_NONCE


def template_epochs_in_window(ticks: int, phase_in_epoch: int) -> Tuple[int, int]:
    """(completed template epochs, leftover ticks into the next epoch).

    ``phase_in_epoch`` = ticks already consumed of the current template epoch at
    window start (0 for a fresh template). Each epoch is exactly 2^32 ticks.
    """
    total = phase_in_epoch + ticks
    return total // S_NONCE, total % S_NONCE


def pocol_window(range_start: int, range_len: int, epoch_ticks: int,
                 ticks_into_epoch: int, ticks: int) -> List[Arc]:
    """Arcs a PoCol miner evaluates during ``ticks``, given its fixed range.

    The miner sweeps [range_start, range_start+range_len) once per epoch of
    ``epoch_ticks`` ticks (epoch_ticks >= range_len; the excess is post-range
    low-power parking). Returns the arcs actually evaluated; used for the exact
    within-epoch disjointness verification on truncated final epochs.
    """
    arcs: List[Arc] = []
    t = ticks_into_epoch
    remaining = ticks
    while remaining > 0:
        in_epoch = min(remaining, epoch_ticks - t)
        scanned_from = min(t, range_len)
        scanned_to = min(t + in_epoch, range_len)
        if scanned_to > scanned_from:
            arcs.append(((range_start + scanned_from) % S_NONCE,
                         scanned_to - scanned_from))
        t = (t + in_epoch) % epoch_ticks
        remaining -= in_epoch
    return arcs
