# Reproducibility Appendix

All results in the revised manuscript are produced by the scripts in
`experiments/` and read from `results/data/*.csv`. The manuscript text, tables,
and figures are generated from those same CSVs (single source of truth), so they
are mutually consistent by construction.

## Environment
- Python 3.11
- `pip install pandas numpy matplotlib scipy xlsxwriter python-docx pytest reportlab pillow`

## One command to reproduce everything
```bash
python experiments/run_all_revision_experiments.py     # data + figures
python -m pytest tests/ -v                              # unit tests
python docs/build_revised_manuscript.py                # revised DOCX
python docs/build_revised_pdf.py                        # revised PDF
```

## Seeds
- Count: 30 per scenario.
- Generation: deterministic, `seed_i = base + i`, base = 20260101, i = 0..29
  (i.e. seeds 20260101 … 20260130).

## Fixed parameters
| Group | Parameter | Value(s) |
|---|---|---|
| Horizon | simulation horizon | 24 h (86,400 s) |
| PoW | miner counts | 50, 100, 500, 1000 |
| PoW | block interval | 600 s (Bitcoin-like) |
| PoW | block subsidy / fees (base) | 3.125 BTC / 0.30 BTC |
| PoW | coin price (low/med/high) | 20,000 / 60,000 / 100,000 USD |
| PoW | electricity price | 0.03 / 0.05 / 0.10 USD/kWh |
| PoW | spend ratio κ | 0.80 |
| PoW | miner efficiency | 21.5 J/TH |
| PoS | validator counts | 100, 500, 1000, 5000 |
| PoS | hardware power | 10 / 100 / 500 W |
| PoS | uptime | 0.90 / 0.99 / 1.00 |
| Carbon | γ (low/avg/high) | 0.05 / 0.475 / 0.82 kgCO₂e/kWh |
| Comm | peer degree | 4, 8, 16 |
| Comm | transaction rate | 1, 10, 100 tx/s |
| Comm | block size | 0.5 / 1 / 2 MB |

## Per-seed stochastic draws (source of std / CI)
- PoW: number of blocks ~ Poisson(horizon / block_interval); coin price × (1 +
  N(0, 0.05)); fees × (1 + N(0, 0.40)) clamped ≥ 0; hashpower shares ~
  Dirichlet(1, …, 1).
- PoS: per-validator power × (1 + N(0, 0.10)); per-validator uptime + N(0, 0.01)
  clamped to [0, 1].

## Output files
| File | Contents |
|---|---|
| `pow_miner_scaling_summary.csv` | Table 2, Fig. 1 |
| `pow_price_sensitivity_summary.csv` | Table 3, Fig. 2 |
| `pos_validator_scaling_summary.csv` | Table 4, Fig. 3 |
| `carbon_gamma_sensitivity_summary.csv` | Table 5, Fig. 4 |
| `communication_energy_summary.csv` | Table 6, Fig. 5 |
| `validation_fixed_power.csv` | Table 7 |
| `reproducibility_summary.csv` | Fig. 6, key headline numbers |
| `*_raw.csv` | full per-seed values for each experiment |

## Headline numbers (24 h horizon)
- PoW network energy (any miner count, base economics): ≈ 467.5 GWh/day
  (95% CI ± 17.1 GWh) — invariant to miner count.
- PoW vs coin price: 155.8 (20k) → 467.5 (60k) → 779.1 (100k) GWh/day.
- PoS standard server: 238.8 (100) → 2,386.8 (1000) → 11,930.3 (5000) kWh/day.
- Carbon (PoW, average γ): ≈ 222,052 t/day; (PoS, average γ): ≈ 1,128 kg/day.
- Communication (peer 8, 1 MB): 15.0 (1 tx/s) → 1,455.2 (100 tx/s) kWh/day.
- PoW/PoS energy ratio: ≈ 196,846×.
- Validation (E = P·T): max relative error 0.00.
