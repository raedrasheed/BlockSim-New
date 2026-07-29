"""Stage 5B1B exact B1 zero-block model + implementation-independent reference.

The engine bug reconciled here: B1 (all miners on one ordered candidate path)
advances the *unique* frontier at `max_i H_i` (== H_total/N homogeneous). Over the
fixed horizon T the frontier evaluates

    M = unique_rate · T           (distinct candidate headers)

Bernoulli(p) trials, p = 1/(H_total · target). The exact no-success probability is

    log P_zero_exact = Σ_g M_g · log1p(−p_g)          (== M · log1p(−p) for constant p)
    P_zero_exact = exp(log P_zero_exact) = (1−p)^M

computed in arbitrary precision (mpmath). The Poisson value exp(−Σ M_g p_g) is
reported ONLY as an approximation with its error.

For every B1 config here M < S (the frontier covers < one template domain within T),
so there are 0 full (exhausted) generations and 1 partial final generation of M
candidates. The generation-level record is emitted for transparency.

`direct_reference_sampler` samples the number of successes ~ Binomial(round(M), p)
directly — it never calls the engine's winner-selection — and reports the observed
zero frequency, an independent Monte-Carlo cross-check of the exact arithmetic.
"""

from __future__ import annotations
import mpmath as mp

mp.mp.dps = 50


def unique_search_rate(rates, homogeneous: bool = True) -> float:
    """B1 unique-frontier rate = max_i H_i (== H_total/N when homogeneous)."""
    return float(max(rates)) if rates else 0.0


def exact_zero_block(network_hash_rate_hps: float, N: int, T: float,
                     target_interval_s: float, mu: float,
                     hetero_rates=None, model_version: str = "b1-exact-1") -> dict:
    p = mp.mpf(1) / (mp.mpf(network_hash_rate_hps) * mp.mpf(target_interval_s))
    unique_rate = (mp.mpf(max(hetero_rates)) if hetero_rates
                   else mp.mpf(network_hash_rate_hps) / N)         # H/N homogeneous
    S = mp.mpf(mu) / p                                             # domain size (p·S = mu)
    M = unique_rate * mp.mpf(T)                                    # unique candidate evaluations

    full_generations = int(mp.floor(M / S))                       # exhausted full sweeps
    partial_candidates = M - full_generations * S                 # partial final generation
    # per-generation record (constant p): full sweeps of S + one partial sweep
    gens = []
    for g in range(full_generations):
        gens.append(dict(template_generation_id=g, unique_candidate_evaluations=float(S),
                         exhausted=True, partial=False, p=float(p)))
    gens.append(dict(template_generation_id=full_generations,
                     unique_candidate_evaluations=float(partial_candidates),
                     exhausted=False, partial=True, p=float(p)))

    log_pzero = M * mp.log1p(-p)                                   # Σ_g M_g log1p(-p_g)
    pzero_exact = mp.e ** log_pzero
    lam = M * p
    pzero_poisson = mp.e ** (-lam)
    abs_err = abs(pzero_exact - pzero_poisson)
    rel_err = abs_err / pzero_exact if pzero_exact > 0 else mp.mpf(0)
    return dict(
        miner_count=N, analytical_model_version=model_version,
        unique_search_rate_hps=float(unique_rate), full_domain_size=float(S),
        p=float(p), expected_unique_candidate_evaluations=float(M),
        expected_full_template_generations=full_generations,
        expected_partial_generation_candidates=float(partial_candidates),
        lambda_=float(lam),
        expected_zero_block_probability_exact=float(pzero_exact),
        expected_zero_block_probability_poisson=float(pzero_poisson),
        poisson_absolute_error=float(abs_err), poisson_relative_error=float(rel_err),
        generations=gens)


def direct_reference_sampler(network_hash_rate_hps: float, N: int, T: float,
                             target_interval_s: float, mu: float, n_samples: int,
                             seed: int) -> dict:
    """Independent Monte-Carlo: successes ~ Binomial(round(M), p); zero-block iff 0.
    Does NOT use the scenario engine or its winner selection."""
    import numpy as np
    p = 1.0 / (network_hash_rate_hps * target_interval_s)
    M = int(round((network_hash_rate_hps / N) * T))
    rng = np.random.default_rng(seed)
    successes = rng.binomial(M, p, size=n_samples)
    zeros = int((successes == 0).sum())
    return dict(n_samples=n_samples, zeros=zeros, zero_frequency=zeros / n_samples,
                M=M, p=p)


def clopper_pearson(k: int, n: int, alpha: float):
    """Exact two-sided Clopper-Pearson interval for a binomial proportion."""
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def b1_exact_table(network_hash_rate_hps: float = 141e12, T: float = 10000.0,
                   target_interval_s: float = 600.0, mu: float = 2.0,
                   counts=(100, 200, 300, 400, 500)) -> list:
    return [exact_zero_block(network_hash_rate_hps, N, T, target_interval_s, mu)
            for N in counts]
