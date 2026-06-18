# Change Log — Major Revision

This revision addresses Reviewer 1 and Reviewer 2. It changes the methodology,
the code, the experiments, the figures, and the manuscript.

## Manuscript (sections changed)
- **Title**: now "Extending BlockSim with **Consensus-Aware** Energy and Carbon
  Footprint Modeling for Sustainable Blockchain Evaluation".
- **Abstract**: rewritten — distinguishes economically driven PoW from
  validator-count-driven PoS; removes "validated"; positions tool as
  scenario-based; mentions γ sensitivity, communication energy, 30-seed
  statistics.
- **Keywords**: added Proof of Work, Proof of Stake, Carbon Footprint, Energy
  Modeling, Consensus Mechanisms, Sustainability.
- **§1 Introduction**: rewritten to explain the economic drivers of PoW energy,
  the PoW/PoS distinction, and the Ethereum Merge correction; explicit
  contribution list.
- **§2 Background**: added §2.2 (energy/carbon studies) and new §2.3 "Energy
  Consumption, Permissionlessness, and Sybil Resistance" with Sedlmeir et al.,
  Platt et al., Platt–Platt–McBurney, De Vries.
- **§4 Consensus-Aware Energy Consumption Models** (new): §4.1 PoW economic,
  §4.2 PoS validator, §4.3 communication, §4.4 carbon (Eqs. 1–7).
- **§5 Implementation in BlockSim** (new): describes `Models/Energy` classes,
  configurable inputs, backward compatibility.
- **§6 Experimental Setup**: reproducibility table (Table 1); 30-seed
  methodology with mean/std/95% CI.
- **§7 Results**: entirely new — §7.1 PoW vs miners (invariance), §7.2 PoW vs
  price/reward/electricity, §7.3 PoS vs validators, §7.4 carbon vs γ, §7.5
  communication vs computation, §7.6 sanity checks + literature-order.
- **§8 Discussion & Threats to Validity**: strengthened; seven explicit
  limitations.
- **§9 Conclusion**: rewritten.
- **References**: de-duplicated, reformatted, and extended with [4], [6], [7],
  [8], [15].
- **Figures**: six new figures (energy vs miners; energy vs price; energy vs
  validators; carbon vs γ; computation vs communication; PoW vs PoS orders),
  all with error bars and appropriate log/separate axes. Old misleading overlay
  figures removed.
- **Tables**: seven tables (reproducibility; PoW miner scaling; PoW economic
  sensitivity; PoS scaling; carbon vs γ; communication; E=P·T validation).

## Code (files added)
- `Models/Energy/__init__.py`
- `Models/Energy/energy_models.py` — `PowEconomicEnergyModel`,
  `PosValidatorEnergyModel`, `CommunicationEnergyModel`, `CarbonFootprintModel`,
  `GAMMA_SCENARIOS`.
- `Models/Energy/scenarios.py` — named scenarios, seed-based stochastic runners,
  statistics helpers (mean/std/95% CI/seed list).
- `experiments/_common.py`, `run_pow_miner_scaling.py`,
  `run_pow_price_sensitivity.py`, `run_pos_validator_scaling.py`,
  `run_carbon_gamma_sensitivity.py`, `run_communication_energy_analysis.py`,
  `run_all_revision_experiments.py`.
- `tests/test_energy_models.py` — 11 unit tests, including the six required ones.
- `docs/manuscript_content.py`, `docs/build_revised_manuscript.py`,
  `docs/build_revised_pdf.py` — single-source manuscript renderers.

## Code (existing files)
- No existing BlockSim model files were modified; the extension is additive and
  backward compatible. The previously selected model in `InputsConfig.py`
  remains unchanged so existing simulations continue to run.

## Experiments / results (files added under `results/`)
- `results/data/*.csv` — raw per-seed and summary (mean/std/95% CI) CSVs for all
  five experiments, plus `validation_fixed_power.csv` and
  `reproducibility_summary.csv`.
- `results/figures/*.png` and `*.pdf` — six figures.

## Backward compatibility / breaking changes
- None. The energy package is self-contained and imported only by the new
  experiment scripts and tests. Existing models, `Main.py`, and `InputsConfig.py`
  are untouched.
