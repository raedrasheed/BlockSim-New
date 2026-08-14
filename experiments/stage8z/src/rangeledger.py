"""Stage 8Z — range ledger with verifiable dynamic work reassignment.

The ledger owns the epoch's candidate domain and is the single authority on who may
scan what. It exists so that dynamic reassignment is *machine-verifiable* rather than
asserted (brief section 14).

Model
-----
The epoch domain ``[0, S)`` is partitioned into one disjoint slot per **installed**
miner. Slots of miners that the policy has not activated are simply unscanned; they
sit in the *residual pool*. Each active miner holds an ordered list of half-open
candidate chunks and scans them in order.

Reassignment is a **global re-partition**: every currently-unscanned candidate — the
untouched tails of active miners' chunks plus the residual pool — is merged and
re-split hash-proportionally among the currently active miners. A re-partition is
triggered when a miner would otherwise run out of work while residual remains, and
when a woken reserve joins. Because the split is hash-proportional, all active miners
again finish simultaneously, which is precisely what removes the staggered-completion
parking loss that cost Stage 8Y's P4 3.8 pp of realized hash capacity.

Enforced invariants (each has a dedicated test)
-----------------------------------------------
1. no candidate index is owned by two miners simultaneously
2. no already-scanned candidate is ever reassigned
3. no completed segment is rescanned
4. every transfer has a unique event id and an immutable ownership history
5. source ownership ends strictly before target ownership begins
6. owned + scanned + residual partitions the domain exactly at all times
7. re-partition never changes the domain size
8. no exact-input duplicate hashes can be produced
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Interval = Tuple[int, int]


def _normalise(intervals: Sequence[Interval]) -> List[Interval]:
    """Sort and merge touching/overlapping intervals."""
    xs = sorted((s, e) for s, e in intervals if e > s)
    if not xs:
        return []
    out = [list(xs[0])]
    for s, e in xs[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(a, b) for a, b in out]


def _total(intervals: Sequence[Interval]) -> int:
    return sum(e - s for s, e in intervals)


def _take(intervals: List[Interval], amount: int) -> Tuple[List[Interval], List[Interval]]:
    """Split an interval list into (first ``amount`` candidates, remainder)."""
    head, rest, need = [], [], int(amount)
    for s, e in intervals:
        if need <= 0:
            rest.append((s, e))
            continue
        L = e - s
        if L <= need:
            head.append((s, e))
            need -= L
        else:
            head.append((s, s + need))
            rest.append((s + need, e))
            need = 0
    return head, rest


@dataclass
class TransferEvent:
    event_id: int
    epoch_key: tuple
    time: float
    from_owner: Optional[int]        # None = residual pool (never-activated slot)
    to_owner: int
    intervals: List[Interval]
    candidates: int
    reason: str


@dataclass
class EpochLedger:
    """Authority over one epoch's candidate domain."""

    epoch_key: tuple
    domain: int
    slots: List[Interval]                       # one per installed miner
    owned: Dict[int, List[Interval]] = field(default_factory=dict)
    residual: List[Interval] = field(default_factory=list)
    scanned: List[Interval] = field(default_factory=list)
    transfers: List[TransferEvent] = field(default_factory=list)
    _next_event: int = 0
    repartitions: int = 0

    # ---------------- construction ----------------
    @classmethod
    def create(cls, epoch_key: tuple, domain: int, slots: List[Interval],
               active_ids: Sequence[int]) -> "EpochLedger":
        act = set(active_ids)
        owned = {i: [slots[i]] for i in sorted(act) if slots[i][1] > slots[i][0]}
        residual = _normalise([slots[i] for i in range(len(slots)) if i not in act])
        return cls(epoch_key=epoch_key, domain=domain, slots=slots, owned=owned,
                   residual=residual)

    # ---------------- queries ----------------
    def owned_candidates(self, miner: int) -> int:
        return _total(self.owned.get(miner, []))

    def residual_candidates(self) -> int:
        return _total(self.residual)

    def scanned_candidates(self) -> int:
        return _total(_normalise(self.scanned))

    def owned_remaining(self) -> int:
        """Candidates still owned by an active miner (excludes the residual pool)."""
        return sum(_total(v) for v in self.owned.values())

    def unscanned_total(self) -> int:
        return self.owned_remaining() + _total(self.residual)

    def is_exhausted(self) -> bool:
        """The epoch is complete when no ACTIVE miner has owned work left.

        The residual pool (slots of miners the policy never activated) is expected to
        stay unscanned under a no-reassignment policy; it must not block completion,
        or the network stalls after one sweep.
        """
        return self.owned_remaining() == 0

    # ---------------- scanning ----------------
    def commit_scan(self, miner: int, upto: int) -> List[Interval]:
        """Consume the first ``upto`` candidates of ``miner``'s ownership.

        Returns the exact intervals scanned so the caller can log them. The consumed
        candidates leave ownership permanently and can never be reassigned or
        rescanned — invariants 2 and 3.
        """
        cur = self.owned.get(miner, [])
        head, rest = _take(cur, upto)
        if head:
            self.scanned.extend(head)
        self.owned[miner] = rest
        return head

    # ---------------- reassignment ----------------
    def repartition(self, active: Sequence[int], weights: Dict[int, float],
                    now: float, reason: str) -> int:
        """Merge every unscanned candidate and re-split it across ``active``.

        Hash-proportional weights make all active miners finish simultaneously.
        Returns the number of transfer events recorded.
        """
        act = [i for i in active if weights.get(i, 0.0) > 0.0]
        if not act:
            return 0
        pool: List[Interval] = list(self.residual)
        origin: List[Tuple[Optional[int], List[Interval]]] = [(None, list(self.residual))]
        for i, iv in list(self.owned.items()):
            if iv:
                pool.extend(iv)
                origin.append((i, list(iv)))
            self.owned[i] = []
        self.residual = []
        pool = _normalise(pool)
        total = _total(pool)
        if total == 0:
            self.owned = {i: [] for i in act}
            return 0

        wsum = sum(weights[i] for i in act)
        shares, acc = [], 0
        for k, i in enumerate(act):
            amt = total - acc if k == len(act) - 1 else int(total * weights[i] / wsum)
            shares.append((i, max(0, amt)))
            acc += shares[-1][1]

        events = 0
        rest = pool
        new_owned: Dict[int, List[Interval]] = {}
        for i, amt in shares:
            chunk, rest = _take(rest, amt)
            new_owned[i] = chunk
            if chunk:
                # attribute the source purely for reporting; ownership itself is
                # atomic - the old owner's claim ended above, before this one begins.
                src = self._source_of(origin, chunk[0][0])
                if src != i:
                    self._next_event += 1
                    self.transfers.append(TransferEvent(
                        event_id=self._next_event, epoch_key=self.epoch_key, time=now,
                        from_owner=src, to_owner=i, intervals=list(chunk),
                        candidates=_total(chunk), reason=reason))
                    events += 1
        self.owned = new_owned
        self.repartitions += 1
        return events

    @staticmethod
    def _source_of(origin, index: int) -> Optional[int]:
        for who, ivs in origin:
            for s, e in ivs:
                if s <= index < e:
                    return who
        return None

    # ---------------- verification ----------------
    def verify(self) -> Dict[str, object]:
        """Machine-checkable invariant report."""
        owned_all: List[Interval] = []
        for iv in self.owned.values():
            owned_all.extend(iv)
        scanned_n = _total(_normalise(self.scanned))
        overlap_owner = 0
        flat = sorted((s, e, m) for m, iv in self.owned.items() for s, e in iv)
        for a, b in zip(flat, flat[1:]):
            if b[0] < a[1]:
                overlap_owner += 1
        merged_scanned = _normalise(self.scanned)
        rescanned = _total(self.scanned) - scanned_n
        # owned/residual must not intersect anything already scanned
        conflict = 0
        for s, e in _normalise(owned_all + self.residual):
            for ss, ee in merged_scanned:
                if max(s, ss) < min(e, ee):
                    conflict += 1
        cover = scanned_n + _total(_normalise(owned_all + self.residual))
        return {
            "owner_overlaps": overlap_owner,
            "rescanned_candidates": rescanned,
            "scanned_vs_owned_conflicts": conflict,
            "partition_error": self.domain - cover,
            "transfer_ids_unique": len({t.event_id for t in self.transfers})
                                   == len(self.transfers),
            "transfers": len(self.transfers),
            "repartitions": self.repartitions,
            "reassigned_candidates": sum(t.candidates for t in self.transfers),
        }
