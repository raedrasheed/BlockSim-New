"""Stage 8X — isolated discrete-event mining engine.

Design notes
------------
This engine deliberately does **not** import ``InputsConfig``, ``Main``,
``Scheduler``, ``Event`` or ``Statistics``. Those bind the model id, the miner
population and the ``Block`` class at *import* time and share a single global RNG,
which makes a 300-run paired matrix impossible (see the Phase-1 audit, A3/A4).
The BlockSim *semantics* that matter are preserved and re-implemented against an
injected, immutable configuration:

* a min-heap event queue keyed on ``(time, sequence)`` for deterministic ordering;
* gossip block propagation with delay ``~ Exp(mean = Bdelay = 0.42 s)`` to all peers;
* longest-chain acceptance with a deterministic tie-break (first-seen wins);
* stale work is abandoned the moment a miner accepts a better tip.

Protocols
---------
``POW``    Traditional competitive PoW. Each miner owns a *distinct* template
           (its own coinbase), searches its own candidate space independently and
           sequentially, and rolls its own extranonce locally and instantly when
           it exhausts a template. It is ACTIVE for the entire horizon.

``POCOL``  PoCol. One common immutable template per epoch; the epoch domain is
           partitioned into N equal disjoint miner-owned ranges (miner i owns
           ``[i*L, (i+1)*L)``); a miner evaluates only its own range; on completing
           it, with no remaining legitimate work in the round, it transitions
           ACTIVE -> LOW_POWER and waits for the next legitimate wake-up event:
           a new accepted block, or receipt of the refreshed common template once
           the whole domain has been swept (the documented liveness rule, audit
           finding A5). No reserve miners, no useful-work floor, no coarse or
           single-handoff reassignment, no dynamic borrowing.

``POWMT``  Declared secondary diagnostic only: competitive PoW in which every
           miner shares the *same* common template as PoCol and starts at an
           independent uniform random offset. This is the only configuration in
           which exact candidate-input duplication is non-degenerate.
"""

from __future__ import annotations

import heapq
import math
import random
import time as _time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from experiments.stage8x.config.asic import S21_PRO, ASICProfile
from experiments.stage8x.config import difficulty as diffmod
from experiments.stage8x.config.seeds import derive_stream_seed
from experiments.stage8x.config.stage8x_config import (
    PROTO_POCOL,
    PROTO_POW,
    PROTO_POW_MT,
    RunConfig,
)
from experiments.stage8x.simulator import hashing
from experiments.stage8x.simulator.powerstate import PowerStateLedger

GENESIS_ID = 0
#: Representable candidate-index space per template (see hashing.EXTRANONCE_BITS).
MAX_CANDIDATE_INDEX = hashing.MAX_CANDIDATE_INDEX


# --------------------------------------------------------------------------
# Internal structures
# --------------------------------------------------------------------------
@dataclass
class _Assignment:
    template_id: tuple
    abs_base: int           # absolute candidate index of cursor 0 (for interval logs)
    length: int             # L, candidates in this assignment
    winners: List[int]      # winning offsets within [0, length) (already relative)
    cursor: int = 0         # candidates already evaluated in this assignment
    scan_start_cursor: int = 0
    scan_start_time: float = 0.0
    wrap_domain: int = 0    # >0 for POWMT: absolute indices wrap modulo this
    wrap_offset: int = 0    # POWMT: absolute start offset in the shared domain


@dataclass
class _Miner:
    id: int
    tip: int = GENESIS_ID
    epoch: int = 0
    roll: int = 0
    token: int = 0
    assign: Optional[_Assignment] = None


@dataclass
class RunResult:
    """Everything recorded for one physical run."""

    run_id: str
    protocol: str
    n_miners: int
    seed: int
    seed_index: int

    # hardware / difficulty
    miner_hashrate_THs: float = 0.0
    aggregate_hashrate_THs: float = 0.0
    active_power_W_per_miner: float = 0.0
    aggregate_full_power_W: float = 0.0
    difficulty: float = 0.0
    target_hex: str = ""
    q_per_candidate: float = 0.0
    simulation_seconds: float = 0.0
    epoch_sweep_s: float = 0.0
    nonce_domain: int = 0
    range_per_miner: int = 0

    # service
    accepted_blocks: int = 0
    closed_rounds: int = 0
    blocks_created: int = 0
    stale_blocks: int = 0
    stale_rate: Optional[float] = None
    blocks_per_hour: float = 0.0
    mean_block_interval: Optional[float] = None
    median_block_interval: Optional[float] = None
    sd_block_interval: Optional[float] = None
    p95_block_interval: Optional[float] = None
    block_intervals: List[float] = field(default_factory=list)

    # physical work
    total_evaluations: int = 0
    unique_evaluations: int = 0
    duplicate_evaluations: int = 0
    duplicate_ratio: Optional[float] = None
    distinct_nonce_values: int = 0
    nonce_value_reuse_ratio: Optional[float] = None
    n_templates: int = 0

    # power states
    active_miner_seconds: float = 0.0
    low_power_miner_seconds: float = 0.0
    low_power_fraction: float = 0.0
    power_state_summary: Dict[str, float] = field(default_factory=dict)

    # diagnostics
    range_completions: int = 0
    epoch_exhaustions: int = 0
    domain_artifact_exhaustions: int = 0
    work_accounting_error: float = 0.0
    execution_time_seconds: float = 0.0


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------
class Stage8XEngine:
    def __init__(self, cfg: RunConfig, profile: ASICProfile = S21_PRO) -> None:
        self.cfg = cfg
        self.profile = profile
        self.spec: diffmod.DifficultySpec = cfg.spec
        self.n = cfg.n_miners
        self.T = cfg.horizon_s
        self.h = profile.hashrate_hps
        self.L = self.spec.range_per_miner
        self.S = self.spec.nonce_domain
        self.q = self.spec.q_per_candidate

        # --- per-purpose, per-miner RNG streams (this is what makes runs paired) ---
        self.rng_search = [
            random.Random(derive_stream_seed(cfg.seed, "search", i)) for i in range(self.n)
        ]
        self.rng_net = [
            random.Random(derive_stream_seed(cfg.seed, "net", i)) for i in range(self.n)
        ]
        self.rng_tpl = [
            random.Random(derive_stream_seed(cfg.seed, "tpl", i)) for i in range(self.n)
        ]
        self.rng_offset = [
            random.Random(derive_stream_seed(cfg.seed, "offset", i)) for i in range(self.n)
        ]

        self.miners = [_Miner(id=i) for i in range(self.n)]
        self.power = PowerStateLedger(self.n, self.T)
        self.ledger = hashing.ScanLedger()

        # block store: id -> (prev, height, miner, timestamp)
        self.blocks: Dict[int, Tuple[int, int, Optional[int], float]] = {
            GENESIS_ID: (-1, 0, None, 0.0)
        }
        self._next_block_id = 1
        self.blocks_created = 0

        # PoCol epoch bookkeeping
        self._epoch_active: Dict[tuple, int] = {}
        self._epoch_completed: Dict[tuple, List[int]] = {}
        self._mt_winners: Dict[tuple, List[int]] = {}

        # diagnostics
        self.range_completions = 0
        self.epoch_exhaustions = 0
        self.domain_artifact_exhaustions = 0

        self._heap: List[tuple] = []
        self._seq = 0
        self.now = 0.0

    # ---------------- event queue ----------------
    def _push(self, t: float, kind: str, payload: tuple) -> None:
        if t > self.T:
            return
        self._seq += 1
        heapq.heappush(self._heap, (float(t), self._seq, kind, payload))

    # ---------------- assignment ----------------
    def _new_assignment(self, m: _Miner, now: float) -> _Assignment:
        proto = self.cfg.protocol
        if proto == PROTO_POW:
            tpl = ("PW", m.id, m.tip, m.roll)
            winners = hashing.sample_winners(self.rng_search[m.id], self.L, self.q)
            a = _Assignment(template_id=tpl, abs_base=0, length=self.L, winners=winners)
        elif proto == PROTO_POCOL:
            tpl = ("PC", m.tip, m.epoch)
            winners = hashing.sample_winners(self.rng_search[m.id], self.L, self.q)
            a = _Assignment(template_id=tpl, abs_base=m.id * self.L,
                            length=self.L, winners=winners)
        elif proto == PROTO_POW_MT:
            tpl = ("MT", m.tip, m.epoch)
            key = tpl
            if key not in self._mt_winners:
                r = random.Random(derive_stream_seed(self.cfg.seed, "mtepoch",
                                                     abs(hash(key)) % (10 ** 12)))
                self._mt_winners[key] = hashing.sample_winners(r, self.S, self.q)
            off = self.rng_offset[m.id].randrange(self.S)
            shared = self._mt_winners[key]
            # relative winner offsets along this miner's wrapped scan of length L
            winners = sorted(
                j for j in ((w - off) % self.S for w in shared) if j < self.L
            )
            a = _Assignment(template_id=tpl, abs_base=off, length=self.L,
                            winners=winners, wrap_domain=self.S, wrap_offset=off)
        else:  # pragma: no cover - guarded by config
            raise ValueError(f"unknown protocol {proto}")

        if a.abs_base + a.length > MAX_CANDIDATE_INDEX and a.wrap_domain == 0:
            self.domain_artifact_exhaustions += 1
        a.scan_start_cursor = 0
        a.scan_start_time = float(now)
        return a

    def _record_scan(self, m: _Miner, upto_cursor: int, now: float) -> None:
        """Log the candidate interval [scan_start_cursor, upto_cursor) of this scan.

        Advancing both the cursor watermark *and* the scan clock is what keeps
        ``W_total == h * t_active``: a segment already logged must never be
        re-derived from elapsed time by a later call.
        """
        a = m.assign
        if a is None:
            return
        if upto_cursor <= a.scan_start_cursor:
            a.scan_start_time = float(now)
            return
        if a.wrap_domain:
            s = (a.wrap_offset + a.scan_start_cursor) % a.wrap_domain
            length = upto_cursor - a.scan_start_cursor
            if s + length <= a.wrap_domain:
                self.ledger.record(a.template_id, s, s + length)
            else:
                self.ledger.record(a.template_id, s, a.wrap_domain)
                self.ledger.record(a.template_id, 0, s + length - a.wrap_domain)
        else:
            self.ledger.record(a.template_id,
                               a.abs_base + a.scan_start_cursor,
                               a.abs_base + upto_cursor)
        a.scan_start_cursor = upto_cursor
        a.scan_start_time = float(now)

    def _cursor_now(self, m: _Miner, now: float) -> int:
        a = m.assign
        advanced = int((float(now) - a.scan_start_time) * self.h)
        return min(a.length, a.scan_start_cursor + max(0, advanced))

    def _schedule_work(self, m: _Miner, now: float) -> None:
        """Schedule the miner's next decision point: solution or range completion."""
        a = m.assign
        a.scan_start_time = float(now)
        nxt = None
        for w in a.winners:
            if w >= a.cursor:
                nxt = w
                break
        if nxt is not None:
            dt = (nxt - a.cursor + 1) / self.h
            self._push(now + dt, "solution", (m.id, m.token, nxt))
        else:
            dt = (a.length - a.cursor) / self.h
            self._push(now + dt, "range_done", (m.id, m.token))

    def _reassign(self, m: _Miner, now: float, new_tip: int, epoch: int = 0) -> None:
        """Abandon current work (logging what was actually evaluated) and restart."""
        if m.assign is not None:
            self._record_scan(m, self._cursor_now(m, now), now)
            self._leave_epoch(m, now, completed=False)
        m.tip = new_tip
        m.epoch = epoch
        m.roll = 0
        m.token += 1
        m.assign = self._new_assignment(m, now)
        self.power.to_active(m.id, now)
        self._enter_epoch(m)
        self._schedule_work(m, now)

    # ---------------- PoCol epoch bookkeeping ----------------
    def _enter_epoch(self, m: _Miner) -> None:
        if self.cfg.protocol != PROTO_POCOL:
            return
        key = (m.tip, m.epoch)
        self._epoch_active[key] = self._epoch_active.get(key, 0) + 1

    def _leave_epoch(self, m: _Miner, now: float, completed: bool) -> None:
        if self.cfg.protocol != PROTO_POCOL:
            return
        key = (m.tip, m.epoch)
        if self.power.state[m.id] == "ACTIVE":
            self._epoch_active[key] = max(0, self._epoch_active.get(key, 0) - 1)
        if completed:
            self._epoch_completed.setdefault(key, []).append(m.id)
        if not completed:
            # miner left for a new tip; it no longer waits on this epoch
            lst = self._epoch_completed.get(key)
            if lst and m.id in lst:
                lst.remove(m.id)

    def _maybe_refresh_epoch(self, key: tuple, now: float) -> None:
        """Global domain exhaustion: every member swept its range without success."""
        if self._epoch_active.get(key, 0) != 0:
            return
        waiting = self._epoch_completed.get(key) or []
        if not waiting:
            return
        self.epoch_exhaustions += 1
        tip, epoch = key
        for mid in list(waiting):
            m = self.miners[mid]
            if m.tip != tip or m.epoch != epoch:
                continue
            delay = self.rng_tpl[mid].expovariate(1.0 / self.cfg.prop_delay_mean_s)
            self._push(now + delay, "template", (mid, m.token, epoch + 1))
        self._epoch_completed[key] = []

    # ---------------- event handlers ----------------
    def _on_solution(self, mid: int, tok: int, w: int) -> None:
        m = self.miners[mid]
        if m.token != tok or m.assign is None:
            return
        a = m.assign
        a.cursor = w + 1
        self._record_scan(m, a.cursor, self.now)

        bid = self._next_block_id
        self._next_block_id += 1
        prev = m.tip
        self.blocks[bid] = (prev, self.blocks[prev][1] + 1, mid, self.now)
        self.blocks_created += 1

        for j in range(self.n):
            if j == mid:
                continue
            delay = self.rng_net[j].expovariate(1.0 / self.cfg.prop_delay_mean_s)
            self._push(self.now + delay, "recv_block", (j, bid))

        self._reassign(m, self.now, bid, epoch=0)

    def _on_range_done(self, mid: int, tok: int) -> None:
        m = self.miners[mid]
        if m.token != tok or m.assign is None:
            return
        a = m.assign
        a.cursor = a.length
        self._record_scan(m, a.length, self.now)
        self.range_completions += 1

        if self.cfg.protocol == PROTO_POCOL:
            # No further legitimate work in this round: ACTIVE -> LOW_POWER.
            key = (m.tip, m.epoch)
            self._epoch_active[key] = max(0, self._epoch_active.get(key, 0) - 1)
            self._epoch_completed.setdefault(key, []).append(mid)
            self.power.to_low_power(mid, self.now)
            self._maybe_refresh_epoch(key, self.now)
        else:
            # Traditional PoW: roll the local extranonce instantly, no downtime.
            m.roll += 1
            m.epoch += 1
            m.token += 1
            m.assign = self._new_assignment(m, self.now)
            self._schedule_work(m, self.now)

    def _on_template(self, mid: int, tok: int, new_epoch: int) -> None:
        m = self.miners[mid]
        if m.token != tok:
            return
        m.epoch = new_epoch
        m.token += 1
        m.assign = self._new_assignment(m, self.now)
        self.power.to_active(mid, self.now)
        self._enter_epoch(m)
        self._schedule_work(m, self.now)

    def _on_recv_block(self, node: int, bid: int) -> None:
        m = self.miners[node]
        if self.blocks[bid][1] <= self.blocks[m.tip][1]:
            return                      # not longer: first-seen tie-break keeps the tip
        self._reassign(m, self.now, bid, epoch=0)

    # ---------------- main loop ----------------
    def run(self) -> RunResult:
        t0 = _time.perf_counter()
        for m in self.miners:
            m.assign = self._new_assignment(m, 0.0)
            self._enter_epoch(m)
            self._schedule_work(m, 0.0)

        while self._heap:
            t, _seq, kind, payload = heapq.heappop(self._heap)
            if t > self.T:
                break
            self.now = t
            if kind == "solution":
                self._on_solution(*payload)
            elif kind == "range_done":
                self._on_range_done(*payload)
            elif kind == "recv_block":
                self._on_recv_block(*payload)
            elif kind == "template":
                self._on_template(*payload)

        # close out open scans and residencies at the horizon
        self.now = self.T
        for m in self.miners:
            if m.assign is not None and self.power.state[m.id] == "ACTIVE":
                self._record_scan(m, self._cursor_now(m, self.T), self.T)
        self.power.close(self.T)

        return self._collect(_time.perf_counter() - t0)

    # ---------------- result assembly ----------------
    def _main_chain(self) -> List[int]:
        best = GENESIS_ID
        for m in self.miners:
            hb, hm = self.blocks[best][1], self.blocks[m.tip][1]
            if hm > hb or (hm == hb and m.tip < best):
                best = m.tip
        chain, cur = [], best
        while cur != GENESIS_ID:
            chain.append(cur)
            cur = self.blocks[cur][0]
        chain.reverse()
        return chain

    def _collect(self, wall: float) -> RunResult:
        cfg, spec = self.cfg, self.spec
        chain = self._main_chain()
        ts = [self.blocks[b][3] for b in chain]
        intervals = []
        prev = 0.0
        for t in ts:
            intervals.append(t - prev)
            prev = t

        def _pct(xs, p):
            if not xs:
                return None
            s = sorted(xs)
            if len(s) == 1:
                return s[0]
            k = (len(s) - 1) * p
            lo, hi = math.floor(k), math.ceil(k)
            return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)

        total = self.ledger.total_evaluations
        unique = self.ledger.unique_evaluations()
        dup = total - unique
        distinct_nonces = self.ledger.distinct_nonce_values()
        accepted = len(chain)
        pstate = self.power.summary()

        expected_work = self.h * self.power.active_miner_seconds
        work_err = abs(total - expected_work) / expected_work if expected_work else 0.0

        r = RunResult(
            run_id=cfg.run_id,
            protocol=cfg.protocol,
            n_miners=self.n,
            seed=cfg.seed,
            seed_index=cfg.seed_index,
            miner_hashrate_THs=self.profile.hashrate_ths,
            aggregate_hashrate_THs=self.profile.aggregate_hashrate_ths(self.n),
            active_power_W_per_miner=self.profile.active_power_w,
            aggregate_full_power_W=self.profile.aggregate_active_power_w(self.n),
            difficulty=spec.difficulty,
            target_hex=spec.target_hex,
            q_per_candidate=spec.q_per_candidate,
            simulation_seconds=self.T,
            epoch_sweep_s=cfg.epoch_sweep_s,
            nonce_domain=spec.nonce_domain,
            range_per_miner=spec.range_per_miner,
            accepted_blocks=accepted,
            closed_rounds=accepted,
            blocks_created=self.blocks_created,
            stale_blocks=self.blocks_created - accepted,
            stale_rate=((self.blocks_created - accepted) / self.blocks_created
                        if self.blocks_created else None),
            blocks_per_hour=accepted / (self.T / 3600.0),
            mean_block_interval=(sum(intervals) / len(intervals)) if intervals else None,
            median_block_interval=_pct(intervals, 0.5),
            sd_block_interval=(
                math.sqrt(sum((x - sum(intervals) / len(intervals)) ** 2
                              for x in intervals) / (len(intervals) - 1))
                if len(intervals) > 1 else None
            ),
            p95_block_interval=_pct(intervals, 0.95),
            block_intervals=intervals,
            total_evaluations=total,
            unique_evaluations=unique,
            duplicate_evaluations=dup,
            duplicate_ratio=(dup / total) if total else None,
            distinct_nonce_values=distinct_nonces,
            nonce_value_reuse_ratio=(1.0 - distinct_nonces / total) if total else None,
            n_templates=self.ledger.n_templates(),
            active_miner_seconds=self.power.active_miner_seconds,
            low_power_miner_seconds=self.power.low_power_miner_seconds,
            low_power_fraction=self.power.low_power_fraction,
            power_state_summary=pstate,
            range_completions=self.range_completions,
            epoch_exhaustions=self.epoch_exhaustions,
            domain_artifact_exhaustions=self.domain_artifact_exhaustions,
            work_accounting_error=work_err,
            execution_time_seconds=wall,
        )
        return r


def simulate(cfg: RunConfig, profile: ASICProfile = S21_PRO) -> RunResult:
    """Run one physical Stage 8X simulation."""
    return Stage8XEngine(cfg, profile).run()
