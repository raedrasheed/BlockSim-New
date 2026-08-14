"""Stage 8Z — adaptive hash-floor and dynamic work-orchestration engine.

Matched semantics are inherited unchanged: the SHA-256 primitive, the candidate
identity ``(template_id, candidate_index)`` and the exact-duplicate interval ledger
are imported **read-only** from Stage 8X; the hardware registry, composition
definitions, difficulty rule and nonce-domain rule are imported **read-only** from the
frozen Stage 8Y configuration. Neither earlier stage is modified.

Policies
--------
Z0  traditional PoW: distinct per-miner templates, instant local extranonce roll,
    always hashing, heterogeneous rates and powers preserved.
Z1  Stage-8Y energy-aware baseline at a fixed active hash fraction (no floor).
Z2  hash-floor energy-aware selection.
Z3  Z2 + dynamic residual reassignment through the range ledger.
Z4  Z3 + predictive reserve activation with hash-capacity step-up.
Z5  Z4 + rolling-window fair rotation.
"""

from __future__ import annotations

import heapq
import math
import random
import time as _time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from experiments.stage8x.simulator import hashing
from experiments.stage8y.config import difficulty as diffmod
from experiments.stage8y.config import policies as y8pol
from experiments.stage8y.config.hardware import Population

from experiments.stage8z.config import stage8z_config as C
from experiments.stage8z.config.seeds import derive_stream_seed
from experiments.stage8z.src import powerstate8z as ps
from experiments.stage8z.src.rangeledger import EpochLedger

GENESIS_ID = 0


@dataclass
class _Miner:
    id: int
    tip: int = GENESIS_ID
    epoch: int = 0
    roll: int = 0
    token: int = 0
    chunks: List[Tuple[int, int]] = field(default_factory=list)  # PoCol assignment
    scanned_in_assignment: int = 0
    scan_start_time: float = 0.0
    got_reassigned: bool = False
    # PoW-only private assignment
    pw_len: int = 0
    pw_cursor: int = 0
    pw_winners: List[int] = field(default_factory=list)


@dataclass
class RunResult:
    run_id: str = ""
    policy: str = ""
    composition: str = ""
    n_miners: int = 0
    seed: int = 0
    seed_index: int = 0
    phase: str = ""
    tag: str = ""
    horizon_s: float = 0.0
    hash_floor: Optional[float] = None
    reassign_rule: str = ""
    reserve_theta: float = 0.0
    fairness_scheme: str = ""
    fairness_pmin: float = 0.0
    wake_s: float = 0.0

    H_N_Hps: float = 0.0
    P_N_W: float = 0.0
    eta_network_J_per_TH: float = 0.0
    difficulty: float = 0.0
    target_hex: str = ""
    q_per_candidate: float = 0.0
    nonce_domain: int = 0

    n_active_initial: int = 0
    r_count_initial: float = 0.0
    r_hash_initial: float = 0.0
    r_power_initial: float = 0.0

    accepted_blocks: int = 0
    closed_rounds: int = 0
    blocks_created: int = 0
    stale_blocks: int = 0
    blocks_per_hour: float = 0.0
    mean_block_interval: Optional[float] = None
    median_block_interval: Optional[float] = None
    p95_block_interval: Optional[float] = None
    block_intervals: List[float] = field(default_factory=list)

    total_evaluations: int = 0
    unique_evaluations: int = 0
    duplicate_evaluations: int = 0
    duplicate_ratio: Optional[float] = None
    distinct_nonce_values: int = 0
    nonce_value_reuse_ratio: Optional[float] = None
    n_templates: int = 0
    stale_evaluations: float = 0.0
    reassigned_evaluations: float = 0.0
    own_evaluations: float = 0.0

    reassign_events: int = 0
    reassign_candidates: int = 0
    repartitions: int = 0
    reassign_src_class: Dict[str, int] = field(default_factory=dict)
    reassign_dst_class: Dict[str, int] = field(default_factory=dict)
    ledger_violations: Dict[str, int] = field(default_factory=dict)

    reserve_activations: int = 0
    reserve_steps_reached: int = 0
    reserve_activation_times: List[float] = field(default_factory=list)
    reserve_hash_activated: float = 0.0
    reserve_power_activated: float = 0.0
    reserve_found_block: int = 0

    epoch_exhaustions: int = 0
    range_completions: int = 0

    power_state: Dict[str, float] = field(default_factory=dict)
    device_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    blocks_by_miner: Dict[int, int] = field(default_factory=dict)
    active_seconds_by_miner: List[float] = field(default_factory=list)
    longest_inactive_streak_s: float = 0.0
    participation_floor_violations: int = 0

    work_accounting_error: float = 0.0
    execution_time_seconds: float = 0.0
    trace: List[tuple] = field(default_factory=list)


class Stage8ZEngine:
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
        self.slot_len = diffmod.slot_lengths(self.pop, self.spec, y8pol.ALLOC_HASH)
        self.slots = diffmod.slot_bounds(self.slot_len)

        self.rng_net = [random.Random(derive_stream_seed(cfg.seed, "net", i))
                        for i in range(self.n)]
        self.rng_tpl = [random.Random(derive_stream_seed(cfg.seed, "tpl", i))
                        for i in range(self.n)]
        self.rng_search = [random.Random(derive_stream_seed(cfg.seed, "search", i))
                           for i in range(self.n)]
        self.rng_sel = random.Random(derive_stream_seed(cfg.seed, "select", 0))

        self.is_pocol = cfg.policy != C.Z0_POW
        self.floor = cfg.hash_floor or 0.0
        self.uses_reserve = C.uses_reserve(cfg.policy)
        self.reassigns = cfg.reassign_rule != C.R0_NONE

        # ---- active-set selection ----
        if self.is_pocol:
            self.base_active = self._select(self.floor, set())
        else:
            self.base_active = set(range(self.n))
        self.stage_sets: List[set] = [set(self.base_active)]
        if self.uses_reserve:
            acc = set(self.base_active)
            for f in cfg.reserve_steps:
                acc |= self._select(f, acc)
                self.stage_sets.append(set(acc))

        init = [ps.ACTIVE_OWN if i in self.base_active else ps.STANDBY_RESERVE
                for i in range(self.n)]
        if not self.is_pocol:
            init = [ps.ACTIVE_OWN] * self.n
        self.power = ps.WorkloadLedger(self.h, self.p, self.T, init,
                                       hash_floor=self.floor if self.is_pocol else 0.0)
        self.ledger = hashing.ScanLedger()

        self.miners = [_Miner(id=i) for i in range(self.n)]
        self.blocks: Dict[int, Tuple[int, int, Optional[int], float]] = {
            GENESIS_ID: (-1, 0, None, 0.0)}
        self._next_block = 1
        self.blocks_created = 0
        self.blocks_by_miner: Dict[int, int] = {}

        self.epochs: Dict[tuple, EpochLedger] = {}
        self.epoch_winners: Dict[tuple, List[int]] = {}
        self.epoch_active: Dict[tuple, set] = {}
        self.epoch_start: Dict[tuple, float] = {}
        self.epoch_stage: Dict[tuple, int] = {}
        self.epoch_of_tip: Dict[int, int] = {GENESIS_ID: 0}

        # fairness bookkeeping
        self.epoch_participation: List[int] = [0] * self.n
        self.epochs_seen = 0
        self.fair_credit: List[float] = [0.0] * self.n

        self.stale_evals = 0.0
        self.reassigned_evals = 0.0
        self.own_evals = 0.0
        self.range_completions = 0
        self.epoch_exhaustions = 0
        self.reserve_activations = 0
        self.reserve_steps_reached = 0
        self.reserve_times: List[float] = []
        self.reserve_hash = 0.0
        self.reserve_power = 0.0
        self.reserve_found = 0
        self.woken_this_round: set = set()
        self.reassign_events = 0
        self.reassign_candidates = 0
        self.repartitions = 0
        self.reassign_src: Dict[str, int] = {}
        self.reassign_dst: Dict[str, int] = {}
        self.violations = {"owner_overlaps": 0, "rescanned_candidates": 0,
                           "scanned_vs_owned_conflicts": 0, "partition_error": 0}

        self._heap: List[tuple] = []
        self._seq = 0
        self.now = 0.0

    # ---------------- selection ----------------
    def _select(self, floor: float, must_include: set) -> set:
        if floor >= 1.0 - 1e-12:
            return set(range(self.n))
        ids = set(y8pol.select_active(self.pop, y8pol.S4_OPTIMIZE,
                                      target_hash_fraction=floor, rng=self.rng_sel))
        return ids | set(must_include)

    def _fair_select(self, floor: float) -> set:
        """Z5: cheapest set meeting the floor, subject to a participation floor."""
        cfg = self.cfg
        if cfg.fairness_scheme == C.F0_NONE or cfg.fairness_pmin <= 0:
            return self._select(floor, set())
        seen = max(1, self.epochs_seen)
        if cfg.fairness_scheme == C.F3_CLASS:
            need = set()
            for key in sorted(set(self.dev)):
                idx = [i for i in range(self.n) if self.dev[i] == key]
                short = [i for i in idx
                         if self.epoch_participation[i] / seen < cfg.fairness_pmin]
                short.sort(key=lambda i: (self.epoch_participation[i], i))
                need |= set(short[:max(1, int(len(idx) * cfg.fairness_pmin))])
        else:
            need = {i for i in range(self.n)
                    if self.epoch_participation[i] / seen < cfg.fairness_pmin}
            need = set(sorted(need, key=lambda i: (self.epoch_participation[i], i))
                       [:max(1, int(self.n * cfg.fairness_pmin))])
        # meet the floor cheaply given the mandated inclusions
        have = sum(self.h[i] for i in need)
        target = floor * self.pop.total_hashrate_hps
        if have >= target:
            return need
        rest = [i for i in range(self.n) if i not in need]
        rest.sort(key=lambda i: (self.p[i] / self.h[i], -self.h[i], i))
        for i in rest:
            if have >= target:
                break
            need.add(i)
            have += self.h[i]
        return need

    # ---------------- queue ----------------
    def _push(self, t: float, kind: str, payload: tuple) -> None:
        if t > self.T:
            return
        self._seq += 1
        heapq.heappush(self._heap, (float(t), self._seq, kind, payload))

    # ---------------- epoch management ----------------
    def _epoch_key(self, tip: int, epoch: int) -> tuple:
        return ("Z", tip, epoch)

    def _ensure_epoch(self, key: tuple, active: set, now: float) -> EpochLedger:
        if key in self.epochs:
            return self.epochs[key]
        led = EpochLedger.create(key, self.S, self.slots, sorted(active))
        self.epochs[key] = led
        r = random.Random(derive_stream_seed(self.cfg.seed, "epoch",
                                             abs(hash(key)) % (10 ** 12)))
        self.epoch_winners[key] = hashing.sample_winners(r, self.S, self.q)
        self.epoch_active[key] = set(active)
        self.epoch_start[key] = now
        self.epoch_stage[key] = 0
        self.epochs_seen += 1
        for i in active:
            self.epoch_participation[i] += 1
        return led

    def _weights(self, active: Sequence[int]) -> Dict[int, float]:
        return {i: self.h[i] for i in active}

    def _assign_from_ledger(self, m: _Miner, now: float) -> None:
        led = self.epochs[self._epoch_key(m.tip, m.epoch)]
        m.chunks = list(led.owned.get(m.id, []))
        m.scanned_in_assignment = 0
        m.scan_start_time = float(now)

    def _next_event_for(self, m: _Miner, now: float) -> None:
        """Schedule the miner's next decision point (solution or work exhausted)."""
        key = self._epoch_key(m.tip, m.epoch)
        winners = self.epoch_winners.get(key, [])
        remaining = sum(e - s for s, e in m.chunks)
        if remaining <= 0:
            self._push(now, "no_work", (m.id, m.token))
            return
        # first winner in scan order
        offset = 0
        hit = None
        for s, e in m.chunks:
            j = hashing.first_winner_at_or_after(winners, s)
            if j is not None and j < e:
                hit = offset + (j - s)
                break
            offset += e - s
        m.scan_start_time = float(now)
        if hit is not None:
            self._push(now + (hit + 1) / self.h[m.id], "solution", (m.id, m.token))
        else:
            self._push(now + remaining / self.h[m.id], "work_done", (m.id, m.token))

    def _commit(self, m: _Miner, count: int, now: float) -> None:
        """Commit ``count`` scanned candidates from the miner's chunks."""
        if count <= 0:
            m.scan_start_time = float(now)
            return
        key = self._epoch_key(m.tip, m.epoch)
        led = self.epochs.get(key)
        if led is None:
            return
        tpl = key
        scanned = led.commit_scan(m.id, count)
        for s, e in scanned:
            self.ledger.record(tpl, s, e)
        got = sum(e - s for s, e in scanned)
        if m.got_reassigned:
            self.reassigned_evals += got
        else:
            self.own_evals += got
        # shrink the miner's local view
        rest, need = [], got
        for s, e in m.chunks:
            L = e - s
            if need >= L:
                need -= L
            elif need > 0:
                rest.append((s + need, e))
                need = 0
            else:
                rest.append((s, e))
        m.chunks = rest
        m.scan_start_time = float(now)

    def _scanned_since(self, m: _Miner, now: float) -> int:
        return max(0, int((float(now) - m.scan_start_time) * self.h[m.id]))

    def _flush(self, m: _Miner, now: float) -> None:
        if self.is_pocol:
            if m.chunks:
                self._commit(m, min(sum(e - s for s, e in m.chunks),
                                    self._scanned_since(m, now)), now)
        elif self.power.state[m.id] in ps.HASHING_STATES:
            self._pow_record(m, m.scanned_in_assignment
                             + self._scanned_since(m, now), now)

    # ---------------- reassignment ----------------
    def _repartition_wave(self, key: tuple, now: float, reason: str,
                          extra: Sequence[int] = ()) -> bool:
        """Re-split every unscanned candidate across the epoch's available miners.

        Called only when a wave completes or a reserve joins, so the number of
        re-partitions per epoch is O(1) rather than O(number of miners).
        """
        led = self.epochs.get(key)
        if led is None or not self.reassigns:
            return False
        if led.unscanned_total() <= 0:
            return False
        _, tip, epoch = key
        ok_states = (ps.ACTIVE_OWN, ps.ACTIVE_REASSIGNED, ps.LOW_POWER_POST_RANGE)
        extra_set = set(extra)
        active = [i for i in sorted(self.epoch_active[key])
                  if self.miners[i].tip == tip and self.miners[i].epoch == epoch
                  and (self.power.state[i] in ok_states or i in extra_set)]
        if not active:
            return False
        for i in active:
            mm = self.miners[i]
            if mm.chunks and self.power.state[i] in ps.HASHING_STATES:
                self._commit(mm, min(sum(e - s for s, e in mm.chunks),
                                     self._scanned_since(mm, now)), now)
        ev = led.repartition(active, self._weights(active), now, reason)
        self.reassign_events += ev
        self.repartitions += 1
        for t in led.transfers[-ev:] if ev else []:
            self.reassign_candidates += t.candidates
            src = self.dev[t.from_owner] if t.from_owner is not None else "UNASSIGNED"
            self.reassign_src[src] = self.reassign_src.get(src, 0) + t.candidates
            self.reassign_dst[self.dev[t.to_owner]] = \
                self.reassign_dst.get(self.dev[t.to_owner], 0) + t.candidates
        any_work = False
        for i in active:
            mm = self.miners[i]
            mm.token += 1
            mm.got_reassigned = True
            self._assign_from_ledger(mm, now)
            if mm.chunks:
                any_work = True
                self.power.transition(i, ps.ACTIVE_REASSIGNED, now)
                self._next_event_for(mm, now)
            else:
                self.power.transition(i, ps.LOW_POWER_POST_RANGE, now)
        return any_work

    # ---------------- reserve ----------------
    def _reserve_check(self, tip: int, epoch: int) -> None:
        if not self.uses_reserve:
            return
        key = self._epoch_key(tip, epoch)
        if key not in self.epochs:
            return
        stage = self.epoch_stage.get(key, 0)
        if stage >= len(self.stage_sets) - 1:
            return
        h_active = sum(self.h[i] for i in range(self.n)
                       if self.power.state[i] in ps.HASHING_STATES
                       and self.miners[i].tip == tip)
        dt = C.RESERVE_DEADLINE_S - (self.now - self.blocks[tip][3])
        if dt <= 0:
            p_succ = 0.0
        else:
            p_succ = 1.0 - math.exp(-h_active * self.q * dt)
        if p_succ >= self.cfg.reserve_theta:
            return
        # step up
        self.epoch_stage[key] = stage + 1
        self.reserve_steps_reached = max(self.reserve_steps_reached, stage + 1)
        new_set = self.stage_sets[stage + 1]
        added = [i for i in sorted(new_set) if i not in self.epoch_active[key]]
        if not added:
            return
        self.reserve_times.append(self.now)
        for i in added:
            self.epoch_active[key].add(i)
            self.epoch_participation[i] += 1
            self.reserve_activations += 1
            self.reserve_hash += self.h[i]
            self.reserve_power += self.p[i]
            mm = self.miners[i]
            mm.tip, mm.epoch = tip, epoch
            if self.cfg.wake_s > 0:
                self.power.transition(i, ps.WAKING, self.now)
                mm.token += 1
                self._push(self.now + self.cfg.wake_s, "wake_done", (i, mm.token))
            else:
                self.woken_this_round.add(i)
                self._join_epoch(mm, self.now)

    def _join_epoch(self, m: _Miner, now: float) -> None:
        key = self._epoch_key(m.tip, m.epoch)
        led = self.epochs.get(key)
        if led is None:
            self.power.transition(m.id, ps.TEMPLATE_WAIT, now)
            return
        m.token += 1
        if self.reassigns:
            # the joining miner is still in WAKING, so it must be named explicitly or
            # it would be excluded from the split and left with no work at all.
            # The wave assigns, transitions and schedules every participant itself,
            # including this one. Doing any of that again here would schedule a second
            # event under the same token and double-count the miner's evaluations.
            if self._repartition_wave(key, now, "reserve_join", extra=(m.id,)):
                if m.chunks:
                    return
        # no reassignment: take this miner's own untouched slot if still free
        s, e = self.slots[m.id]
        if led.owned.get(m.id) is None and (s, e) in led.residual:
            led.owned[m.id] = [(s, e)]
            led.residual = [iv for iv in led.residual if iv != (s, e)]
        m.chunks = list(led.owned.get(m.id, []))
        m.scanned_in_assignment = 0
        m.scan_start_time = float(now)
        if m.chunks:
            self.power.transition(m.id, ps.ACTIVE_OWN, now)
            self._next_event_for(m, now)
        else:
            self.power.transition(m.id, ps.LOW_POWER_POST_RANGE, now)

    # ---------------- handlers ----------------
    def _on_solution(self, mid: int, tok: int) -> None:
        m = self.miners[mid]
        if m.token != tok:
            return
        if self.is_pocol:
            self._commit(m, self._scanned_since(m, self.now), self.now)
        else:
            self._pow_record(m, m.scanned_in_assignment
                             + self._scanned_since(m, self.now), self.now)
        bid = self._next_block
        self._next_block += 1
        prev = m.tip
        self.blocks[bid] = (prev, self.blocks[prev][1] + 1, mid, self.now)
        self.blocks_created += 1
        self.blocks_by_miner[mid] = self.blocks_by_miner.get(mid, 0) + 1
        if mid in self.woken_this_round:
            self.reserve_found += 1
        for j in range(self.n):
            if j == mid:
                continue
            self._push(self.now + self.rng_net[j].expovariate(
                1.0 / self.cfg.prop_delay_mean_s), "recv_block", (j, bid))
        self.epoch_of_tip[bid] = 0
        self._adopt(m, bid, self.now)

    def _on_work_done(self, mid: int, tok: int) -> None:
        """Miner finished every candidate it owns."""
        m = self.miners[mid]
        if m.token != tok:
            return
        if not self.is_pocol:
            self.range_completions += 1
            self._pow_record(m, m.pw_len, self.now)
            m.roll += 1
            m.token += 1
            self._new_pow_assignment(m, self.now)
            return
        self._commit(m, sum(e - s for s, e in m.chunks), self.now)
        self.range_completions += 1
        self.power.transition(mid, ps.LOW_POWER_POST_RANGE, self.now)
        key = self._epoch_key(m.tip, m.epoch)
        led = self.epochs.get(key)
        if led is None or not led.is_exhausted():
            return
        # A wave has completed: every active miner has finished what it owned.
        # Only now may residual work be re-partitioned, which bounds the number of
        # re-partitions per epoch instead of cascading once per miner completion.
        if self.reassigns and led.residual_candidates() > 0:
            if self._repartition_wave(key, self.now, "wave_complete"):
                return
        self._exhaust_epoch(key, self.now)

    def _on_no_work(self, mid: int, tok: int) -> None:
        m = self.miners[mid]
        if m.token != tok:
            return
        self.power.transition(mid, ps.LOW_POWER_POST_RANGE, self.now)
        key = self._epoch_key(m.tip, m.epoch)
        led = self.epochs.get(key)
        if led is not None and led.is_exhausted():
            if self.reassigns and led.residual_candidates() > 0:
                if self._repartition_wave(key, self.now, "wave_complete"):
                    return
            self._exhaust_epoch(key, self.now)

    def _exhaust_epoch(self, key: tuple, now: float) -> None:
        led = self.epochs[key]
        v = led.verify()
        for k in self.violations:
            self.violations[k] += int(abs(v[k]) if k == "partition_error" else v[k])
        self.epoch_exhaustions += 1
        _, tip, epoch = key
        for i in sorted(self.epoch_active[key]):
            m = self.miners[i]
            if m.tip != tip or m.epoch != epoch:
                continue
            if self.power.state[i] in (ps.WAKING,):
                continue
            self.power.transition(i, ps.TEMPLATE_WAIT, now)
            m.token += 1
            self._push(now + self.rng_tpl[i].expovariate(
                1.0 / self.cfg.prop_delay_mean_s), "template", (i, m.token, epoch + 1))

    def _on_template(self, mid: int, tok: int, new_epoch: int) -> None:
        m = self.miners[mid]
        if m.token != tok:
            return
        self.epoch_of_tip[m.tip] = max(self.epoch_of_tip.get(m.tip, 0), new_epoch)
        m.epoch = new_epoch
        self._start_epoch_for(m, self.now)

    def _on_wake_done(self, mid: int, tok: int) -> None:
        m = self.miners[mid]
        if m.token != tok or self.power.state[mid] != ps.WAKING:
            return
        self.woken_this_round.add(mid)
        m.epoch = self.epoch_of_tip.get(m.tip, 0)
        self._join_epoch(m, self.now)

    def _on_recv_block(self, node: int, bid: int) -> None:
        m = self.miners[node]
        if self.blocks[bid][1] <= self.blocks[m.tip][1]:
            return
        if self.power.state[node] in ps.HASHING_STATES:
            self.stale_evals += self.h[node] * max(0.0, self.now - self.blocks[bid][3])
        self._adopt(m, bid, self.now)

    def _on_reserve_tick(self, tip: int, epoch: int) -> None:
        self._reserve_check(tip, epoch)
        if self.uses_reserve:
            self._push(self.now + C.RESERVE_CHECK_S, "reserve_tick", (tip, epoch))

    # ---------------- round / epoch start ----------------
    def _pow_record(self, m: _Miner, upto: int, now: float) -> None:
        """Log the PoW interval actually evaluated, then advance the scan clock."""
        upto = max(m.scanned_in_assignment, min(m.pw_len, upto))
        if upto > m.scanned_in_assignment:
            self.ledger.record(("PW", m.id, m.tip, m.roll),
                               m.scanned_in_assignment, upto)
            self.own_evals += upto - m.scanned_in_assignment
            m.scanned_in_assignment = upto
        m.pw_cursor = upto
        m.scan_start_time = float(now)

    def _new_pow_assignment(self, m: _Miner, now: float) -> None:
        m.pw_len = self.slot_len[m.id]
        m.pw_cursor = 0
        m.scanned_in_assignment = 0
        m.pw_winners = hashing.sample_winners(self.rng_search[m.id], m.pw_len, self.q)
        m.scan_start_time = float(now)
        nxt = next((w for w in m.pw_winners if w >= 0), None)
        if nxt is not None:
            self._push(now + (nxt + 1) / self.h[m.id], "solution", (m.id, m.token))
        else:
            self._push(now + m.pw_len / self.h[m.id], "work_done", (m.id, m.token))

    def _start_epoch_for(self, m: _Miner, now: float) -> None:
        key = self._epoch_key(m.tip, m.epoch)
        if key not in self.epochs:
            floor = self.floor
            if self.cfg.policy == C.Z5_FAIR:
                active = self._fair_select(floor)
            else:
                active = set(self.base_active)
            self._ensure_epoch(key, active, now)
            if self.uses_reserve:
                self._push(now + C.RESERVE_CHECK_S, "reserve_tick", (m.tip, m.epoch))
        led = self.epochs[key]
        if m.id not in self.epoch_active[key]:
            self.power.transition(m.id, ps.STANDBY_RESERVE, now)
            return
        m.token += 1
        m.got_reassigned = False
        self._assign_from_ledger(m, now)
        if m.chunks:
            self.power.transition(m.id, ps.ACTIVE_OWN, now)
            self._next_event_for(m, now)
        else:
            self.power.transition(m.id, ps.LOW_POWER_POST_RANGE, now)

    def _adopt(self, m: _Miner, new_tip: int, now: float) -> None:
        self._flush(m, now)
        m.tip = new_tip
        m.epoch = 0
        m.roll = 0
        m.token += 1
        m.chunks = []
        m.got_reassigned = False
        self.woken_this_round.discard(m.id)
        if not self.is_pocol:
            self._new_pow_assignment(m, now)
            return
        self._start_epoch_for(m, now)

    # ---------------- main loop ----------------
    def run(self) -> RunResult:
        t0 = _time.perf_counter()
        if self.is_pocol:
            for m in self.miners:
                self._start_epoch_for(m, 0.0)
        else:
            for m in self.miners:
                self._new_pow_assignment(m, 0.0)

        while self._heap:
            t, _s, kind, payload = heapq.heappop(self._heap)
            if t > self.T:
                break
            self.now = t
            if kind == "solution":
                self._on_solution(*payload)
            elif kind == "work_done":
                self._on_work_done(*payload)
            elif kind == "no_work":
                self._on_no_work(*payload)
            elif kind == "recv_block":
                self._on_recv_block(*payload)
            elif kind == "template":
                self._on_template(*payload)
            elif kind == "wake_done":
                self._on_wake_done(*payload)
            elif kind == "reserve_tick":
                self._on_reserve_tick(*payload)

        self.now = self.T
        for m in self.miners:
            if self.power.state[m.id] in ps.HASHING_STATES:
                if self.is_pocol:
                    self._commit(m, min(sum(e - s for s, e in m.chunks),
                                        self._scanned_since(m, self.T)), self.T)
                else:
                    self._pow_record(m, m.scanned_in_assignment
                                     + self._scanned_since(m, self.T), self.T)
        self.power.close(self.T)
        for key, led in self.epochs.items():
            v = led.verify()
            for k in self.violations:
                self.violations[k] += int(abs(v[k]) if k == "partition_error" else v[k])
            self.repartitions = max(self.repartitions, self.repartitions)
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
        cfg, pop = self.cfg, self.pop
        chain = self._main_chain()
        ts = [self.blocks[b][3] for b in chain]
        intervals, prev = [], 0.0
        for t in ts:
            intervals.append(t - prev)
            prev = t

        def _pct(xs, q):
            if not xs:
                return None
            s = sorted(xs)
            if len(s) == 1:
                return s[0]
            k = (len(s) - 1) * q
            lo, hi = math.floor(k), math.ceil(k)
            return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)

        total = self.ledger.total_evaluations
        unique = self.ledger.unique_evaluations()
        pstate = self.power.summary()
        expected = pstate["integral_H_active_hashes"]
        werr = abs(total - expected) / expected if expected else 0.0

        init = y8pol.active_fractions(pop, sorted(self.base_active))
        by_dev: Dict[str, Dict[str, float]] = {}
        for key in sorted(set(self.dev)):
            idx = [i for i in range(self.n) if self.dev[i] == key]
            act = sum(sum(self.power.t[i][s] for s in ps.HASHING_STATES) for i in idx)
            by_dev[key] = {
                "count": len(idx),
                "hash_share_installed": sum(self.h[i] for i in idx) / pop.total_hashrate_hps,
                "active_seconds": act,
                "active_fraction_of_own_time": act / (len(idx) * self.T) if idx else 0.0,
                "blocks_won": sum(self.blocks_by_miner.get(i, 0) for i in idx),
                "n_initially_active": sum(1 for i in idx if i in self.base_active),
            }
        act_by_miner = [sum(self.power.t[i][s] for s in ps.HASHING_STATES)
                        for i in range(self.n)]
        seen = max(1, self.epochs_seen // max(1, 1))
        pmin = cfg.fairness_pmin
        viol = sum(1 for i in range(self.n)
                   if pmin > 0 and self.epoch_participation[i] / max(1, self.epochs_seen)
                   < pmin) if cfg.fairness_scheme != C.F0_NONE else 0

        accepted = len(chain)
        return RunResult(
            run_id=cfg.run_id, policy=cfg.policy, composition=cfg.composition,
            n_miners=self.n, seed=cfg.seed, seed_index=cfg.seed_index,
            phase=cfg.phase, tag=cfg.tag, horizon_s=self.T,
            hash_floor=cfg.hash_floor, reassign_rule=cfg.reassign_rule,
            reserve_theta=cfg.reserve_theta, fairness_scheme=cfg.fairness_scheme,
            fairness_pmin=cfg.fairness_pmin, wake_s=cfg.wake_s,
            H_N_Hps=pop.total_hashrate_hps, P_N_W=pop.total_power_w,
            eta_network_J_per_TH=pop.network_efficiency_j_per_th,
            difficulty=self.spec.difficulty, target_hex=self.spec.target_hex,
            q_per_candidate=self.q, nonce_domain=self.S,
            n_active_initial=init["n_active"], r_count_initial=init["r_count"],
            r_hash_initial=init["r_hash"], r_power_initial=init["r_power"],
            accepted_blocks=accepted, closed_rounds=accepted,
            blocks_created=self.blocks_created,
            stale_blocks=self.blocks_created - accepted,
            blocks_per_hour=accepted / (self.T / 3600.0),
            mean_block_interval=(sum(intervals) / len(intervals)) if intervals else None,
            median_block_interval=_pct(intervals, 0.5),
            p95_block_interval=_pct(intervals, 0.95),
            block_intervals=intervals,
            total_evaluations=total, unique_evaluations=unique,
            duplicate_evaluations=total - unique,
            duplicate_ratio=((total - unique) / total) if total else None,
            distinct_nonce_values=self.ledger.distinct_nonce_values(),
            nonce_value_reuse_ratio=(1.0 - self.ledger.distinct_nonce_values() / total)
            if total else None,
            n_templates=self.ledger.n_templates(),
            stale_evaluations=self.stale_evals,
            reassigned_evaluations=self.reassigned_evals,
            own_evaluations=self.own_evals,
            reassign_events=self.reassign_events,
            reassign_candidates=self.reassign_candidates,
            repartitions=self.repartitions,
            reassign_src_class=dict(self.reassign_src),
            reassign_dst_class=dict(self.reassign_dst),
            ledger_violations=dict(self.violations),
            reserve_activations=self.reserve_activations,
            reserve_steps_reached=self.reserve_steps_reached,
            reserve_activation_times=list(self.reserve_times),
            reserve_hash_activated=self.reserve_hash,
            reserve_power_activated=self.reserve_power,
            reserve_found_block=self.reserve_found,
            epoch_exhaustions=self.epoch_exhaustions,
            range_completions=self.range_completions,
            power_state=pstate, device_stats=by_dev,
            blocks_by_miner=dict(self.blocks_by_miner),
            active_seconds_by_miner=act_by_miner,
            longest_inactive_streak_s=max(
                (max(self.power.episodes[s], default=0.0) for s in ps.PARKED_STATES),
                default=0.0),
            participation_floor_violations=viol,
            work_accounting_error=werr, execution_time_seconds=wall,
            trace=self.power.trace)


def simulate(cfg: C.RunConfig) -> RunResult:
    return Stage8ZEngine(cfg).run()
