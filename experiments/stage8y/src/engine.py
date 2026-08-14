"""Stage 8Y — heterogeneous, energy-aware discrete-event mining engine.

Relationship to Stage 8X
------------------------
Stage 8X is treated as the architectural and reproducibility reference and is never
modified. Stage 8Y **imports** ``experiments.stage8x.simulator.hashing`` read-only so
that the SHA-256 primitive, the candidate-identity definition
``(template_id, candidate_index)`` and the exact-duplicate interval ledger are
provably identical between the two experiment families. Everything else — the
heterogeneous population, the four-state power model, active-set selection, reserve
activation and wake transitions — is new Stage 8Y code.

Matched semantics retained from Stage 8X: min-heap event queue keyed on
``(time, seq)``; gossip propagation ``Exp(mean 0.42 s)`` broadcast to all peers;
longest-chain acceptance with a deterministic first-seen tie-break; stale work
abandoned on adopting a better tip; per-purpose, per-miner RNG streams.

Protocols
---------
``POW``          traditional competitive PoW. Distinct per-miner template, own
                 extranonce path, rolls locally and instantly, always ACTIVE.
``POW_CT``       common-template independent PoW. SECONDARY diagnostic only.
``P0_ALL``       PoCol, every miner active, hash-proportional slots.
``P1_EQUAL``     PoCol, equal slots -> fast miners finish early and park.
``P2_HASHPROP``  PoCol, hash-proportional slots -> equal completion times.
``P3_ENERGY``    PoCol, energy-aware active set held for the horizon.
``P4_RESERVE``   PoCol, staged reserve activation with an explicit wake transition.
"""

from __future__ import annotations

import heapq
import math
import random
import time as _time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Read-only reuse of the Stage 8X hashing primitives (identical candidate semantics).
from experiments.stage8x.simulator import hashing

from experiments.stage8y.config import difficulty as diffmod
from experiments.stage8y.config import policies as pol
from experiments.stage8y.config import stage8y_config as C
from experiments.stage8y.config.hardware import TH, Population
from experiments.stage8y.config.seeds import derive_stream_seed
from experiments.stage8y.src import powerstate as ps

GENESIS_ID = 0


@dataclass
class _Assignment:
    template_id: tuple
    abs_base: int
    length: int
    winners: List[int]
    cursor: int = 0
    scan_start_cursor: int = 0
    scan_start_time: float = 0.0
    wrap_domain: int = 0
    wrap_offset: int = 0


@dataclass
class _Miner:
    id: int
    tip: int = GENESIS_ID
    epoch: int = 0
    roll: int = 0
    token: int = 0
    assign: Optional[_Assignment] = None
    assign_count: int = 0


@dataclass
class RunResult:
    run_id: str = ""
    protocol: str = ""
    composition: str = ""
    n_miners: int = 0
    seed: int = 0
    seed_index: int = 0
    phase: str = ""
    tag: str = ""

    # hardware / difficulty
    H_N_Hps: float = 0.0
    P_N_W: float = 0.0
    eta_network_J_per_TH: float = 0.0
    difficulty: float = 0.0
    target_hex: str = ""
    q_per_candidate: float = 0.0
    nonce_domain: int = 0
    domain_semantics: str = ""
    allocation: str = ""
    selection_rule: str = ""
    target_hash_fraction: Optional[float] = None
    target_count_fraction: Optional[float] = None
    reserve_schedule: str = ""
    trigger_s: float = 0.0
    wake_s: float = 0.0
    horizon_s: float = 0.0

    # initial active set
    n_active_initial: int = 0
    r_count_initial: float = 0.0
    r_hash_initial: float = 0.0
    r_power_initial: float = 0.0

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
    stale_evaluations: float = 0.0
    useful_chain_evaluations: float = 0.0

    # power / energy inputs
    power_state: Dict[str, float] = field(default_factory=dict)
    reserve_activations: int = 0
    stage_max_reached: int = 0
    epoch_exhaustions: int = 0
    range_completions: int = 0

    # fairness / per-device
    device_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    blocks_by_miner: Dict[int, int] = field(default_factory=dict)
    active_seconds_by_miner: List[float] = field(default_factory=list)

    # diagnostics
    work_accounting_error: float = 0.0
    execution_time_seconds: float = 0.0
    trace_h_active: List[tuple] = field(default_factory=list)


class Stage8YEngine:
    def __init__(self, cfg: C.RunConfig) -> None:
        self.cfg = cfg
        self.pop: Population = cfg.population
        self.spec: diffmod.DifficultySpec = cfg.spec
        self.n = self.pop.n_miners
        self.T = cfg.horizon_s
        self.q = self.spec.q_per_candidate
        self.S = self.spec.nonce_domain

        self.h = [m.hashrate_hps for m in self.pop.miners]
        self.p = [m.active_power_w for m in self.pop.miners]
        self.dev = [m.device_key for m in self.pop.miners]

        alloc = cfg.allocation if cfg.protocol != C.POW else pol.ALLOC_HASH
        self.slot_len = diffmod.slot_lengths(self.pop, self.spec, alloc)
        self.slot_bounds = diffmod.slot_bounds(self.slot_len)

        # --- RNG streams (paired across protocols at the same master seed) ---
        self.rng_search = [random.Random(derive_stream_seed(cfg.seed, "search", i))
                           for i in range(self.n)]
        self.rng_net = [random.Random(derive_stream_seed(cfg.seed, "net", i))
                        for i in range(self.n)]
        self.rng_tpl = [random.Random(derive_stream_seed(cfg.seed, "tpl", i))
                        for i in range(self.n)]
        self.rng_offset = [random.Random(derive_stream_seed(cfg.seed, "offset", i))
                           for i in range(self.n)]
        self.rng_select = random.Random(derive_stream_seed(cfg.seed, "select", 0))

        # --- active-set / reserve configuration ---
        self.is_pocol = cfg.protocol in C.POCOL_PROTOCOLS
        self.stage_sets: List[List[int]] = []
        if cfg.protocol == C.P4_RESERVE:
            sched = cfg.reserve_schedule or C.CONF_RESERVE_SCHEDULE
            self.stage_sets = pol.reserve_stage_sets(self.pop, cfg.selection_rule,
                                                     sched, self.rng_select)
            self.initial_active = set(self.stage_sets[0])
        elif cfg.protocol == C.P3_ENERGY:
            ids = pol.select_active(self.pop, cfg.selection_rule,
                                    target_hash_fraction=cfg.target_hash_fraction,
                                    target_count_fraction=cfg.target_count_fraction,
                                    rng=self.rng_select)
            self.initial_active = set(ids)
        else:
            self.initial_active = set(range(self.n))

        init_states = [ps.ACTIVE if i in self.initial_active else ps.STANDBY
                       for i in range(self.n)]
        self.power = ps.PowerStateLedger(self.h, self.p, self.T, init_states)
        self.ledger = hashing.ScanLedger()

        self.miners = [_Miner(id=i) for i in range(self.n)]
        self.blocks: Dict[int, Tuple[int, int, Optional[int], float]] = {
            GENESIS_ID: (-1, 0, None, 0.0)}
        self._next_block_id = 1
        self.blocks_created = 0
        self.blocks_by_miner: Dict[int, int] = {}
        self.block_winner_evals: Dict[int, float] = {}

        self._epoch_active: Dict[tuple, int] = {}
        self._epoch_completed: Dict[tuple, List[int]] = {}
        self._ct_winners: Dict[tuple, List[int]] = {}
        self.stage_of_tip: Dict[int, int] = {GENESIS_ID: 0}
        #: current common-template epoch per tip, so a reserve woken mid-round
        #: joins the epoch the rest of the network is actually on.
        self.epoch_of_tip: Dict[int, int] = {GENESIS_ID: 0}

        self.range_completions = 0
        self.epoch_exhaustions = 0
        self.reserve_activations = 0
        self.stage_max_reached = 0
        self.stale_evaluations = 0.0

        self._heap: List[tuple] = []
        self._seq = 0
        self.now = 0.0

    # ---------------- queue ----------------
    def _push(self, t: float, kind: str, payload: tuple) -> None:
        if t > self.T:
            return
        self._seq += 1
        heapq.heappush(self._heap, (float(t), self._seq, kind, payload))

    # ---------------- assignments ----------------
    def _new_assignment(self, m: _Miner, now: float) -> _Assignment:
        proto = self.cfg.protocol
        i = m.id
        L = self.slot_len[i]
        base = self.slot_bounds[i][0]
        m.assign_count += 1
        if proto == C.POW:
            tpl = ("PW", i, m.tip, m.roll)
            winners = hashing.sample_winners(self.rng_search[i], L, self.q)
            a = _Assignment(tpl, 0, L, winners)
        elif proto == C.POW_CT:
            tpl = ("CT", m.tip, m.epoch)
            if tpl not in self._ct_winners:
                r = random.Random(derive_stream_seed(self.cfg.seed, "ctepoch",
                                                     abs(hash(tpl)) % (10 ** 12)))
                self._ct_winners[tpl] = hashing.sample_winners(r, self.S, self.q)
            off = self.rng_offset[i].randrange(self.S)
            winners = sorted(j for j in ((w - off) % self.S
                                         for w in self._ct_winners[tpl]) if j < L)
            a = _Assignment(tpl, off, L, winners, wrap_domain=self.S, wrap_offset=off)
        else:  # every PoCol policy shares one common immutable template per epoch
            tpl = ("PC", m.tip, m.epoch)
            winners = hashing.sample_winners(self.rng_search[i], L, self.q)
            a = _Assignment(tpl, base, L, winners)
        a.scan_start_cursor = 0
        a.scan_start_time = float(now)
        return a

    def _record_scan(self, m: _Miner, upto: int, now: float) -> None:
        a = m.assign
        if a is None:
            return
        if upto <= a.scan_start_cursor:
            a.scan_start_time = float(now)
            return
        if a.wrap_domain:
            s = (a.wrap_offset + a.scan_start_cursor) % a.wrap_domain
            length = upto - a.scan_start_cursor
            if s + length <= a.wrap_domain:
                self.ledger.record(a.template_id, s, s + length)
            else:
                self.ledger.record(a.template_id, s, a.wrap_domain)
                self.ledger.record(a.template_id, 0, s + length - a.wrap_domain)
        else:
            self.ledger.record(a.template_id, a.abs_base + a.scan_start_cursor,
                               a.abs_base + upto)
        a.scan_start_cursor = upto
        a.scan_start_time = float(now)

    def _cursor_now(self, m: _Miner, now: float) -> int:
        a = m.assign
        adv = int((float(now) - a.scan_start_time) * self.h[m.id])
        return min(a.length, a.scan_start_cursor + max(0, adv))

    def _schedule_work(self, m: _Miner, now: float) -> None:
        a = m.assign
        a.scan_start_time = float(now)
        nxt = None
        for w in a.winners:
            if w >= a.cursor:
                nxt = w
                break
        if nxt is not None:
            self._push(now + (nxt - a.cursor + 1) / self.h[m.id], "solution",
                       (m.id, m.token, nxt))
        else:
            self._push(now + (a.length - a.cursor) / self.h[m.id], "range_done",
                       (m.id, m.token))

    def _flush(self, m: _Miner, now: float) -> None:
        """Log the work actually performed, then drop the assignment."""
        if m.assign is not None:
            self._record_scan(m, self._cursor_now(m, now), now)
            self._leave_epoch(m)

    def _activate(self, m: _Miner, now: float, epoch: int) -> None:
        m.epoch = epoch
        m.token += 1
        m.assign = self._new_assignment(m, now)
        self.power.transition(m.id, ps.ACTIVE, now)
        self._enter_epoch(m)
        self._schedule_work(m, now)

    # ---------------- epoch bookkeeping (PoCol only) ----------------
    def _enter_epoch(self, m: _Miner) -> None:
        if not self.is_pocol:
            return
        key = (m.tip, m.epoch)
        self._epoch_active[key] = self._epoch_active.get(key, 0) + 1

    def _leave_epoch(self, m: _Miner) -> None:
        if not self.is_pocol:
            return
        key = (m.tip, m.epoch)
        if self.power.state[m.id] == ps.ACTIVE:
            self._epoch_active[key] = max(0, self._epoch_active.get(key, 0) - 1)
        lst = self._epoch_completed.get(key)
        if lst and m.id in lst:
            lst.remove(m.id)

    def _maybe_refresh_epoch(self, key: tuple, now: float) -> None:
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

    # ---------------- reserve control (P4) ----------------
    def _schedule_stages(self, tip: int, t0: float) -> None:
        if self.cfg.protocol != C.P4_RESERVE:
            return
        for s in range(1, len(self.stage_sets)):
            self._push(t0 + s * self.cfg.trigger_s, "stage_up", (tip, s))

    def _apply_stage_to_miner(self, m: _Miner, stage: int, now: float) -> None:
        """Wake ``m`` if the stage's active set now includes it.

        Only a STANDBY reserve may be activated. A miner in LOW_POWER has already
        swept its slot for the current epoch, so re-activating it would rescan a
        completed range and manufacture exact duplicate work. It legitimately wakes
        at the next template refresh instead.
        """
        if m.id in self.stage_sets[stage] and self.power.state[m.id] == ps.STANDBY:
            self.reserve_activations += 1
            if self.cfg.wake_s > 0:
                self.power.transition(m.id, ps.WAKING, now)
                m.token += 1
                self._push(now + self.cfg.wake_s, "wake_done", (m.id, m.token))
            else:
                self._activate(m, now, self.epoch_of_tip.get(m.tip, 0))

    def _on_stage_up(self, tip: int, stage: int) -> None:
        if self.stage_of_tip.get(tip, 0) >= stage:
            return
        self.stage_of_tip[tip] = stage
        self.stage_max_reached = max(self.stage_max_reached, stage)
        for m in self.miners:
            if m.tip == tip:
                self._apply_stage_to_miner(m, stage, self.now)

    def _on_wake_done(self, mid: int, tok: int) -> None:
        m = self.miners[mid]
        if m.token != tok or self.power.state[mid] != ps.WAKING:
            return
        self._activate(m, self.now, self.epoch_of_tip.get(m.tip, 0))

    # ---------------- event handlers ----------------
    def _on_solution(self, mid: int, tok: int, w: int) -> None:
        m = self.miners[mid]
        if m.token != tok or m.assign is None:
            return
        m.assign.cursor = w + 1
        self._record_scan(m, m.assign.cursor, self.now)

        bid = self._next_block_id
        self._next_block_id += 1
        prev = m.tip
        self.blocks[bid] = (prev, self.blocks[prev][1] + 1, mid, self.now)
        self.blocks_created += 1
        self.blocks_by_miner[mid] = self.blocks_by_miner.get(mid, 0) + 1
        self.block_winner_evals[bid] = float(w + 1)

        for j in range(self.n):
            if j == mid:
                continue
            delay = self.rng_net[j].expovariate(1.0 / self.cfg.prop_delay_mean_s)
            self._push(self.now + delay, "recv_block", (j, bid))

        self.stage_of_tip[bid] = 0
        self.epoch_of_tip[bid] = 0
        self._schedule_stages(bid, self.now)
        self._adopt(m, bid, self.now)

    def _on_range_done(self, mid: int, tok: int) -> None:
        m = self.miners[mid]
        if m.token != tok or m.assign is None:
            return
        m.assign.cursor = m.assign.length
        self._record_scan(m, m.assign.length, self.now)
        self.range_completions += 1

        if self.is_pocol:
            key = (m.tip, m.epoch)
            self._epoch_active[key] = max(0, self._epoch_active.get(key, 0) - 1)
            self._epoch_completed.setdefault(key, []).append(mid)
            self.power.transition(mid, ps.LOW_POWER, self.now)
            self._maybe_refresh_epoch(key, self.now)
        else:
            m.roll += 1
            m.epoch += 1
            m.token += 1
            m.assign = self._new_assignment(m, self.now)
            self._schedule_work(m, self.now)

    def _on_template(self, mid: int, tok: int, new_epoch: int) -> None:
        m = self.miners[mid]
        if m.token != tok:
            return
        self.epoch_of_tip[m.tip] = max(self.epoch_of_tip.get(m.tip, 0), new_epoch)
        self._activate(m, self.now, new_epoch)

    def _on_recv_block(self, node: int, bid: int) -> None:
        m = self.miners[node]
        if self.blocks[bid][1] <= self.blocks[m.tip][1]:
            return
        self.stale_evaluations += self.h[node] * max(
            0.0, self.now - self.blocks[bid][3]) if self.power.state[node] == ps.ACTIVE else 0.0
        self._adopt(m, bid, self.now)

    def _adopt(self, m: _Miner, new_tip: int, now: float) -> None:
        """Accept a new tip: abandon stale work and restart under the round's policy."""
        self._flush(m, now)
        m.tip = new_tip
        m.epoch = 0
        m.roll = 0
        m.token += 1
        m.assign = None

        if self.cfg.protocol == C.P4_RESERVE:
            stage = self.stage_of_tip.get(new_tip, 0)
            self.stage_max_reached = max(self.stage_max_reached, stage)
            if m.id in self.stage_sets[stage]:
                if self.power.state[m.id] == ps.WAKING:
                    return                       # let the wake complete
                self._activate(m, now, 0)
            else:
                self.power.transition(m.id, ps.STANDBY, now)
        elif self.cfg.protocol == C.P3_ENERGY:
            if m.id in self.initial_active:
                self._activate(m, now, 0)
            else:
                self.power.transition(m.id, ps.STANDBY, now)
        else:
            self._activate(m, now, 0)

    # ---------------- main loop ----------------
    def run(self) -> RunResult:
        t0 = _time.perf_counter()
        for m in self.miners:
            if m.id in self.initial_active:
                self._activate(m, 0.0, 0)
        self._schedule_stages(GENESIS_ID, 0.0)

        while self._heap:
            t, _s, kind, payload = heapq.heappop(self._heap)
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
            elif kind == "stage_up":
                self._on_stage_up(*payload)
            elif kind == "wake_done":
                self._on_wake_done(*payload)

        self.now = self.T
        for m in self.miners:
            if m.assign is not None and self.power.state[m.id] == ps.ACTIVE:
                self._record_scan(m, self._cursor_now(m, self.T), self.T)
        self.power.close(self.T)
        return self._collect(_time.perf_counter() - t0)

    # ---------------- results ----------------
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
        cfg, spec, pop = self.cfg, self.spec, self.pop
        chain = self._main_chain()
        ts = [self.blocks[b][3] for b in chain]
        intervals, prev = [], 0.0
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
        pstate = self.power.summary()
        expected = pstate["integral_H_active_hashes"]
        werr = abs(total - expected) / expected if expected else 0.0

        init = pol.active_fractions(pop, sorted(self.initial_active))
        by_dev: Dict[str, Dict[str, float]] = {}
        for key in sorted(set(self.dev)):
            idx = [i for i in range(self.n) if self.dev[i] == key]
            by_dev[key] = {
                "count": len(idx),
                "hash_share_installed": sum(self.h[i] for i in idx) / pop.total_hashrate_hps,
                "power_share_installed": sum(self.p[i] for i in idx) / pop.total_power_w,
                "active_seconds": sum(self.power.t[i][ps.ACTIVE] for i in idx),
                "low_seconds": sum(self.power.t[i][ps.LOW_POWER] for i in idx),
                "standby_seconds": sum(self.power.t[i][ps.STANDBY] for i in idx),
                "waking_seconds": sum(self.power.t[i][ps.WAKING] for i in idx),
                "active_fraction_of_own_time": (
                    sum(self.power.t[i][ps.ACTIVE] for i in idx) / (len(idx) * self.T)
                    if idx and self.T else 0.0),
                "blocks_won": sum(self.blocks_by_miner.get(i, 0) for i in idx),
                "n_initially_active": sum(1 for i in idx if i in self.initial_active),
            }

        accepted = len(chain)
        r = RunResult(
            run_id=cfg.run_id, protocol=cfg.protocol, composition=cfg.composition,
            n_miners=self.n, seed=cfg.seed, seed_index=cfg.seed_index,
            phase=cfg.phase, tag=cfg.tag,
            H_N_Hps=pop.total_hashrate_hps, P_N_W=pop.total_power_w,
            eta_network_J_per_TH=pop.network_efficiency_j_per_th,
            difficulty=spec.difficulty, target_hex=spec.target_hex,
            q_per_candidate=spec.q_per_candidate, nonce_domain=spec.nonce_domain,
            domain_semantics=spec.domain_semantics,
            allocation=cfg.allocation, selection_rule=cfg.selection_rule,
            target_hash_fraction=cfg.target_hash_fraction,
            target_count_fraction=cfg.target_count_fraction,
            reserve_schedule=(",".join(f"{x:.2f}" for x in cfg.reserve_schedule)
                              if cfg.reserve_schedule else ""),
            trigger_s=cfg.trigger_s, wake_s=cfg.wake_s, horizon_s=self.T,
            n_active_initial=init["n_active"], r_count_initial=init["r_count"],
            r_hash_initial=init["r_hash"], r_power_initial=init["r_power"],
            accepted_blocks=accepted, closed_rounds=accepted,
            blocks_created=self.blocks_created,
            stale_blocks=self.blocks_created - accepted,
            stale_rate=((self.blocks_created - accepted) / self.blocks_created
                        if self.blocks_created else None),
            blocks_per_hour=accepted / (self.T / 3600.0),
            mean_block_interval=(sum(intervals) / len(intervals)) if intervals else None,
            median_block_interval=_pct(intervals, 0.5),
            sd_block_interval=(math.sqrt(
                sum((x - sum(intervals) / len(intervals)) ** 2 for x in intervals)
                / (len(intervals) - 1)) if len(intervals) > 1 else None),
            p95_block_interval=_pct(intervals, 0.95),
            block_intervals=intervals,
            total_evaluations=total, unique_evaluations=unique,
            duplicate_evaluations=dup,
            duplicate_ratio=(dup / total) if total else None,
            distinct_nonce_values=distinct_nonces,
            nonce_value_reuse_ratio=(1.0 - distinct_nonces / total) if total else None,
            n_templates=self.ledger.n_templates(),
            stale_evaluations=self.stale_evaluations,
            useful_chain_evaluations=sum(self.block_winner_evals.get(b, 0.0)
                                         for b in chain),
            power_state=pstate,
            reserve_activations=self.reserve_activations,
            stage_max_reached=self.stage_max_reached,
            epoch_exhaustions=self.epoch_exhaustions,
            range_completions=self.range_completions,
            device_stats=by_dev,
            blocks_by_miner=dict(self.blocks_by_miner),
            active_seconds_by_miner=[self.power.t[i][ps.ACTIVE] for i in range(self.n)],
            work_accounting_error=werr,
            execution_time_seconds=wall,
            trace_h_active=self.power.trace,
        )
        return r


def simulate(cfg: C.RunConfig) -> RunResult:
    return Stage8YEngine(cfg).run()
