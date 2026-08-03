"""Stage-2B target-coupled PoCol search core.

Corrects the two scientific defects the final review found in the Stage-2A core:

* **Success is coupled to the actual fixed target** (S2B-1).  A nonce succeeds iff the
  real SHA-256 digest of ``header || nonce`` satisfies ``digest_int <= template.target``.
  The template and its target are fixed for the round; there is NO dynamic difficulty and
  NO sampled/placed winner.  The finite domain therefore genuinely admits zero, one, or
  multiple solutions, and full-domain exhaustion with no block.  The winning block is the
  first valid solution reached in simulation time under the event-ordering contract.

* **The per-nonce work primitive is the real digest** (``WORK_PRIMITIVE``), computed for
  every evaluated nonce and recorded in the executable evaluation ledger.

``solution_after_units`` and the without-replacement winner sampler are removed entirely —
no stored-but-unused success field remains.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

SUCCESS_MODEL = "TARGET_COUPLED_SHA256_DIGEST_LEQ_TARGET"
WORK_PRIMITIVE = "SHA256(header||nonce)"
_FULL_256 = (1 << 256) - 1
_TWO_256 = 1 << 256


def sha256_int(header_bytes: bytes, nonce: int) -> int:
    """Real per-nonce work primitive: the 256-bit integer digest of header || nonce."""
    h = hashlib.sha256(header_bytes + int(nonce).to_bytes(8, "big")).digest()
    return int.from_bytes(h, "big")


def target_for_difficulty(difficulty: int) -> int:
    """The fixed confirmatory target threshold for a difficulty (higher => harder).

    ``target = floor((2^256 - 1) / difficulty)``; a nonce is a solution iff its digest is
    ``<= target``.  The per-nonce success probability is ``(target + 1) / 2^256``.
    """
    return _FULL_256 // max(1, int(difficulty))


def success_probability(target: int) -> float:
    """Per-nonce success probability ``p = (target + 1) / 2^256`` for a fixed target."""
    return (int(target) + 1) / _TWO_256


@dataclass(frozen=True)
class Template:
    """The IMMUTABLE common block template committed once per round.

    Success is coupled to the fixed ``target``: ``is_solution(nonce)`` is true iff the real
    SHA-256 digest of ``header_bytes || nonce`` is ``<= target``.
    """

    TemplateID: str
    RoundID: str
    header_bytes: bytes
    difficulty: int
    nonce_domain_size: int
    target: int

    def digest(self, nonce: int) -> int:
        return sha256_int(self.header_bytes, nonce)

    def is_solution(self, nonce: int) -> bool:
        return self.digest(nonce) <= self.target


def make_template(RoundID: str, difficulty: int, nonce_domain_size: int,
                  seed: int) -> Template:
    """Commit an immutable template whose success is coupled to the fixed target."""
    header = hashlib.sha256(f"{RoundID}|{difficulty}|{nonce_domain_size}|{seed}"
                            .encode()).digest()
    return Template(TemplateID=f"tpl-{RoundID}", RoundID=RoundID, header_bytes=header,
                    difficulty=difficulty, nonce_domain_size=nonce_domain_size,
                    target=target_for_difficulty(difficulty))


def partition_domain(nonce_domain_size: int,
                     participant_ids: Sequence) -> Dict[object, Tuple[int, int]]:
    """Deterministic DISJOINT contiguous partition of ``[0, D)`` over sorted miners.

    Returns ``{MinerID: (range_start, range_end)}`` with ``range_end`` exclusive.  The
    ranges are pairwise disjoint and their union is exactly ``[0, D)`` (SCI-1/SCI-2).
    """
    ids = sorted(participant_ids, key=str)
    n = len(ids)
    if n == 0:
        return {}
    base = nonce_domain_size // n
    rem = nonce_domain_size % n
    ranges: Dict[object, Tuple[int, int]] = {}
    start = 0
    for i, mid in enumerate(ids):
        size = base + (1 if i < rem else 0)
        ranges[mid] = (start, start + size)
        start += size
    assert start == nonce_domain_size
    return ranges


@dataclass
class MinerSearchState:
    """Per-active-miner search state under one immutable template."""

    MinerID: object
    AssignmentID: str
    assignment_version: int
    hash_rate: float                 # nonces / second (> 0)
    range_start: int
    range_end: int                   # exclusive
    active_power: float
    idle_power: float
    cursor: int = 0
    searched_count: int = 0
    search_generation: int = 0       # bumped on every committed hash-work event (replay guard)
    completed: bool = False
    completion_kind: Optional[str] = None   # "SOLUTION" | "EXHAUSTED"
    active_start: Optional[float] = None     # ACTIVE_HASHING start time

    def __post_init__(self):
        self.cursor = self.range_start

    def range_size(self) -> int:
        return self.range_end - self.range_start
