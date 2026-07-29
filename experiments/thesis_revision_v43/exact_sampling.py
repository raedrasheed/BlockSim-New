"""Stage 5B1D exact uniform sampling without replacement.

Given a finite domain {0, 1, ..., S-1} and a count k, return EXACTLY k distinct
integers sampled uniformly without replacement — i.e. a uniformly random k-subset,
each of the C(S, k) subsets equally likely. This replaces the Stage-5B1B
`np.unique(rng.integers(0, S, size=k))`, which used with-replacement draws plus
deduplication and therefore returned fewer than k positions on a collision.

Algorithm: Floyd's algorithm for sampling without replacement (Bentley & Floyd,
"Programming Pearls", CACM 1987; see also Knuth TAOCP Vol.2 Alg. S / R). It draws
exactly k times and uses O(k) memory and expected O(k) time, so it never allocates
an array of size S. For k > S/2 (only possible at small S — at thesis scale
k = Binomial(S, p) is tiny) it samples the (S-k)-element complement to keep the work
O(min(k, S-k)); that branch enumerates the small domain and is never reached at
thesis scale.

Guarantees (asserted by callers): len(result) == k and all elements distinct, for
every 0 <= k <= S. The completed exact subset MAY be sorted afterwards (ordering for
earliest-solution search); sorting happens only after the exact k-subset exists,
never as truncation of a larger sample.
"""

from __future__ import annotations
import numpy as np


def _floyd(rng, S: int, m: int):
    """Floyd's algorithm: m distinct uniform integers from [0, S). Draws exactly m
    times from `rng`; O(m) memory/time."""
    selected = set()
    out = []
    # j runs over the last m values [S-m, S-1]; each step adds one new element
    for j in range(S - m, S):
        t = int(rng.integers(0, j + 1))        # uniform in [0, j] inclusive
        if t in selected:
            selected.add(j)
            out.append(j)
        else:
            selected.add(t)
            out.append(t)
    return out


def sample_without_replacement(rng, S, k) -> np.ndarray:
    """Return a sorted numpy int64 array of exactly k distinct positions sampled
    uniformly without replacement from {0, ..., S-1}.

    Raises ValueError for k < 0 or k > S."""
    S = int(S)
    k = int(k)
    if k < 0:
        raise ValueError(f"k must be >= 0, got {k}")
    if k > S:
        raise ValueError(f"k ({k}) must be <= domain size S ({S})")
    if k == 0:
        return np.empty(0, dtype=np.int64)
    if k <= S - k:
        sample = _floyd(rng, S, k)                       # O(k), no size-S allocation
    else:
        # complement strategy (small S only; k tiny at thesis scale so never reached)
        excluded = set(_floyd(rng, S, S - k))
        sample = [i for i in range(S) if i not in excluded]
    arr = np.array(sample, dtype=np.int64)
    arr.sort()                                            # sort AFTER the exact subset exists
    return arr
