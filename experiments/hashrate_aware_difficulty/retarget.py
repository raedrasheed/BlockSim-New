"""D3 dynamic retargeting from accepted-block timestamps.

Rule (documented, Bitcoin-like):
    every `window_blocks` ACCEPTED blocks:
        observed_timespan = t_last_block - t_previous_boundary
        raw = target_timespan / observed_timespan     (target_timespan = window*T)
        adj = clamp(raw, clamp_min, clamp_max)        (default [0.25, 4.0])
        new_difficulty = old_difficulty * adj    <=>  new_target = old_target/adj
Clamping is applied PER RETARGET to the adjustment factor itself; the resulting
target is additionally clamped to the valid 256-bit range. Retargeting never
fires per block unless window_blocks == 1 (a separately labelled mode).
"""
from __future__ import annotations

from . import target as tg


class Retargeter:
    def __init__(self, initial_target, window_blocks=10, clamp_min=0.25,
                 clamp_max=4.0, t_target=600.0):
        if window_blocks < 1:
            raise ValueError("window_blocks must be >= 1")
        if not (0 < clamp_min <= 1 <= clamp_max):
            raise ValueError("clamps must satisfy 0 < min <= 1 <= max")
        self.target = int(initial_target)
        self.window = int(window_blocks)
        self.clamp_min = float(clamp_min)
        self.clamp_max = float(clamp_max)
        self.t_target = float(t_target)
        self._boundary_time = 0.0
        self._blocks_in_window = 0
        self.history = []            # (time, old_target, adj, new_target)

    def current_target(self):
        return self.target

    def current_difficulty(self):
        return tg.difficulty_from_target(self.target)

    def on_block(self, commit_time):
        """Record an ACCEPTED block timestamp; retarget at window boundaries.
        Returns the target to use for subsequent templates."""
        self._blocks_in_window += 1
        if self._blocks_in_window >= self.window:
            observed = float(commit_time) - self._boundary_time
            if observed <= 0:
                observed = 1e-9
            target_timespan = self.window * self.t_target
            raw = target_timespan / observed
            adj = min(self.clamp_max, max(self.clamp_min, raw))
            old = self.target
            # difficulty *= adj  <=>  target /= adj (integer-safe, 256-bit clamp)
            new = int(old / adj)
            self.target = max(0, min(tg.MAX_TARGET, new))
            self.history.append((float(commit_time), old, adj, self.target))
            self._boundary_time = float(commit_time)
            self._blocks_in_window = 0
        return self.target
