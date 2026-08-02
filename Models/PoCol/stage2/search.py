"""Stage-2A scientific PoCol search core.

Adds the pieces the independent review found missing from the Stage-2 core:

* an IMMUTABLE common block template per round (`Template`);
* an explicit FINITE nonce domain `[0, nonce_domain_size)`;
* a DETERMINISTIC DISJOINT partition of the domain into per-miner ranges
  (`partition_domain`);
* per-miner search state (cursor, searched-count, hash rate, powers, range,
  assignment version);
* a real cryptographic work primitive `sha256_int(header || nonce)` evaluated for
  every searched nonce (counted), plus the recorded **success model B** — the exact
  without-replacement sampler that draws the winning nonce position(s) for the round.

Success model (RECORDED): **B — exact without-replacement sampler.**  The winning nonce
is drawn deterministically (seeded by the immutable template header) from the finite
domain without replacement; `solution_after_units` is NOT a success mechanism (it is a
disabled test-injection hook only).  A real SHA-256 digest of `header || nonce` is
computed as the per-nonce modeled work unit and counted, so the search performs genuine
cryptographic work; the success predicate is `nonce in template.winning_nonces`.  Round
duration therefore depends on hash rate, difficulty (domain size / winning depth),
searched nonce positions, and the number of active miners — never on a fixed unit timer.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

SUCCESS_MODEL = "B_EXACT_WITHOUT_REPLACEMENT_SAMPLER"
WORK_PRIMITIVE = "SHA256(header||nonce)"
_FULL_256 = (1 << 256) - 1


def sha256_int(header_bytes: bytes, nonce: int) -> int:
    """Real per-nonce work primitive: the 256-bit integer digest of header || nonce."""
    h = hashlib.sha256(header_bytes + int(nonce).to_bytes(8, "big")).digest()
    return int.from_bytes(h, "big")


def target_for_difficulty(difficulty: int) -> int:
    """The fixed confirmatory target threshold for a difficulty (higher = harder)."""
    return _FULL_256 // max(1, int(difficulty))


class WithoutReplacementSampler:
    """Deterministic exact without-replacement sampler over ``[0, domain_size)``.

    Draws distinct winning positions without replacement, seeded reproducibly, so a
    matched CONTROL and POCOL_IDLE run over the same round use the SAME success
    position(s) (SCI-7).  This is the previously validated sampler method (B).
    """

    def __init__(self, domain_size: int, seed: int):
        self.domain_size = domain_size
        self._state = (int(seed) & _FULL_256) ^ 0x9E3779B97F4A7C15
        self._drawn: set = set()

    def _next_raw(self) -> int:
        # SplitMix64-style deterministic advance (no global RNG, resume-safe).
        self._state = (self._state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return z ^ (z >> 31)

    def draw(self) -> int:
        if len(self._drawn) >= self.domain_size:
            raise ValueError("sampler exhausted: no unused positions remain")
        while True:
            pos = self._next_raw() % self.domain_size
            if pos not in self._drawn:
                self._drawn.add(pos)
                return pos


@dataclass(frozen=True)
class Template:
    """The IMMUTABLE common block template committed once per round."""

    TemplateID: str
    RoundID: str
    header_bytes: bytes
    difficulty: int
    nonce_domain_size: int
    winning_nonces: frozenset
    target: int

    def is_solution(self, nonce: int) -> bool:
        """Success model B: the nonce is a solution iff it is a sampled winning position."""
        return nonce in self.winning_nonces


def make_template(RoundID: str, difficulty: int, nonce_domain_size: int, seed: int,
                  n_winners: int = 1) -> Template:
    """Commit an immutable template with a deterministically sampled winning nonce set."""
    header = hashlib.sha256(f"{RoundID}|{difficulty}|{nonce_domain_size}|{seed}"
                            .encode()).digest()
    sampler = WithoutReplacementSampler(nonce_domain_size, seed=seed)
    winners = frozenset(sampler.draw() for _ in range(max(1, n_winners)))
    return Template(TemplateID=f"tpl-{RoundID}", RoundID=RoundID, header_bytes=header,
                    difficulty=difficulty, nonce_domain_size=nonce_domain_size,
                    winning_nonces=winners, target=target_for_difficulty(difficulty))


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
    completed: bool = False
    completion_kind: Optional[str] = None   # "SOLUTION" | "EXHAUSTED"
    active_start: Optional[float] = None     # ACTIVE_HASHING start time

    def __post_init__(self):
        self.cursor = self.range_start

    def range_size(self) -> int:
        return self.range_end - self.range_start
