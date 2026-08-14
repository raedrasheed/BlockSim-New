# STAGE 8Y — HARDWARE RATIONALE AND SOURCE VERIFICATION

Machine-readable form: `config/hardware_registry.json`.
Retrieval date for every entry: **2026-08-14**.

---

## 1. Devices

| Key | Manufacturer | Model | Generation | h (TH/s) | P (W) | η stated (J/TH) | η derived = P/h | Consistent |
|---|---|---|---|---|---|---|---|---|
| `S21PRO` | Bitmain | Antminer S21 Pro | current high-efficiency | 234 | 3510 | 15.0 | 15.000 | yes |
| `S19XP` | Bitmain | Antminer S19 XP | intermediate | 141 | 3010 | 21.5 | 21.348 | **no — 0.7 % gap** |
| `S19JPRO` | Bitmain | Antminer S19j Pro 104T | older | 104 | 3068 | 29.5 | 29.500 | yes |

Efficiency spread across the registry: **15.0 → 29.5 J/TH, a factor of 1.967**. This
factor is the hard physical ceiling on how much *selection* (as opposed to reduced
participation) can contribute to any energy saving in Stage 8Y, and it is the reason
the experiment can distinguish the two mechanisms at all.

## 2. Sources

| Device | Official source | Status |
|---|---|---|
| S21 Pro | https://support.bitmain.com/hc/en-us/articles/31321354157593-S21-Pro-Specification | article located; numeric table **not retrievable** from this sandbox |
| S21 Pro (secondary) | https://file12.bitmain.com/shop-product-s3/firmware/820cf7da-aa2b-453e-9af1-d4cc258ec630/2025/02/17/10/S21%20Pro%20Product%20Manual%20V3.0.2%20.pdf | host not resolvable from this network |
| S19 XP | https://support.bitmain.com/hc/en-us/articles/8906244096409-S19-XP-Specifications | article located; numeric table **not retrievable** |
| S19j Pro 104T | https://support.bitmain.com/hc/en-us/articles/900006762746-S19j-Pro-Specifications | **verified quote** |

### 2.1 What was actually verified

`support.bitmain.com` returns **HTTP 403** to the sandboxed fetcher used here
(Zendesk edge protection), and `file12.bitmain.com` does not resolve from this
network. The official article URLs were located for all three devices.

For the **S19j Pro 104T** the official page content was obtained and quotes:

> "The S19j Pro 104T has a hashrate of 104 ± 3 % TH/s with a power consumption of
> 3068 ± 5 % Watts at 25 ℃. Model 240-Cb, SHA256, BTC/BCH."

3068 / 104 = 29.5 J/TH exactly, matching the stated efficiency.

For the **S21 Pro** and the **S19 XP** the numeric tables could not be retrieved.
The figures used are the widely-published nominal values, and the registry marks
them `manufacturer_certified: "url_located_content_not_retrievable"`. **They must be
confirmed against the official pages before publication.** They are not presented as
verified, and no substitution was made silently. The S21 Pro values are additionally
the same ones already used and frozen in Stage 8X, which keeps the two experiment
families directly comparable.

### 2.2 Tolerances

Bitmain publishes these as *typical* values: hash rate ± 3 %, power on wall and
efficiency on wall ± 5 % at 25 ℃. Stage 8Y uses the nominal figures with **no
stochastic device variation**, which is recorded as a limitation. A ± 5 % power
tolerance is of the same order as several of the effects measured here, so
device-level variation is a genuine threat to the precision of any single number.

## 3. Modelling conventions

1. **`(h, P)` are primary; `η` is derived.** Energy is `P × t`, so `P` must be the
   quantity that enters the accounting. Deriving `η = P/h` guarantees internal
   consistency. Where the manufacturer's stated `η` disagrees (S19 XP: 21.5 stated
   vs 21.348 derived) the discrepancy is documented, and the derived value is used.
   The gap is 0.7 %, well inside the published ± 5 % power tolerance.
2. **No invented low-power state.** No Bitmain document publishes an idle, standby
   or low-power operating point for any of these machines. Stage 8Y therefore
   assigns **no device-specific parked figure**. All parked power is
   `P_low = α · P_active` with α ∈ {0, 0.05, 0.10, 0.25, 0.50}, and every report
   states verbatim: *these values are model-based sensitivity assumptions and are
   not manufacturer-certified Antminer low-power operating modes.* α = 0 is an
   idealized theoretical lower bound, not a physically validated state.
3. **No invented wake-power curve.** No manufacturer wake-transition power profile
   exists, so Stage 8Y takes the conservative option offered by the brief: a waking
   miner draws **full active power** while performing **no hashing**. This choice is
   unfavourable to PoCol and is frozen before execution.
4. **No reseller data.** Only manufacturer support/product documentation is cited.
   Where it could not be retrieved, that is stated rather than substituted.

## 4. Why these three devices

* **S21 Pro** — the current-generation efficiency leader and the Stage 8X device;
  including it makes Stage 8X the homogeneous limit of Stage 8Y (composition H0).
* **S19j Pro 104T** — a widely deployed older unit at nearly twice the J/TH. It
  supplies the low-efficiency end of the spread that energy-aware selection can act
  on.
* **S19 XP** — an intermediate generation. Without it, heterogeneity is binary and
  every selection rule degenerates to "pick all the new machines". The third class
  is what makes the S4 optimisation a non-trivial problem and lets composition H4
  represent a realistic multi-generation network.

## 5. Composition rationale

| ID | Mix | Why |
|---|---|---|
| H0 | 100 % S21PRO | homogeneous control; isolates everything that is *not* heterogeneity |
| H1 | 75 / 25 S21PRO / S19JPRO | a network that has largely refreshed |
| H2 | 50 / 50 | balanced two-generation reference case |
| H3 | 25 / 75 | dominated by older capacity with a high-efficiency minority |
| H4 | 20 % S21PRO / 30 % S19XP / 50 % S19JPRO | three generations with the newest a minority, reflecting gradual turnover: older units keep running while marginally profitable |

H4's shares were fixed on the turnover argument above **before any Stage 8Y run was
executed**, and were not tuned toward or away from the 50 % acceptance threshold.
Selecting a hardware mixture that maximises the measured saving would be exactly the
manufactured result the brief forbids; the composition sweep H0–H4 is reported in
full precisely so that the dependence of the result on the mixture is visible rather
than hidden behind one favourable case.
