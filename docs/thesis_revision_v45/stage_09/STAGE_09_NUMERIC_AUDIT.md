# Stage 9 — Numeric Audit

Every percentage and headline number inserted into the redline was verified against
`STAGE_09_NUMERIC_PROVENANCE.csv` and the frozen source files, and confirmed to carry its
comparator at each point of use in the redline `document.xml` (programmatic text scan).

| Number | Must map to | Present in redline with comparator? |
|---|---|---|
| 90.39% | accepted-block retention vs **no-floor PoCol control (S00)** | YES — "retained 90.39% of the accepted-block output of the no-floor PoCol control" |
| 55.05% | calculated energy reduction vs **within-run power-null reference** | YES — "55.05% calculated low-power-state energy reduction relative to the within-run power-null reference"; CI 54.95%–55.15% |
| 44.95% | total-energy reduction vs **W01 matched same-template PoW control** | YES — "44.95% less total energy … active-capacity-matched same-template PoW control" |
| 67.70% | accepted-block ratio vs **W01 matched PoW** | YES — "produced 67.70% of the control's accepted blocks" |
| 19.3% | energy per accepted block vs **W01 matched PoW** | YES — "about 19.3% less energy per accepted block" |
| 87.9% | physical evaluations vs **W01 matched PoW** | YES — "about 87.9% fewer physical evaluations" |
| 5.219× | median round duration vs **W01 matched PoW** | YES — "5.219-times larger median round duration" |
| 8.420833333 kWh | Stage-6A fixed-horizon energy invariant | UNCHANGED (retained macro-scale finding) |
| NOT LICENSED | joint Stage-8S and Stage-8U claims | YES — stated in both result boxes and Table 7.7 |

Population/horizon/seed count stated at first use of the reduced-scale results ("20
miners, 300 s horizon, 1600-nonce domain, difficulty 1000; 12 fresh paired seeds").
Cross-checks:

* 90.39% = 160.8 / 177.9 (S03/S00 accepted blocks) — matches
  `STAGE_08S_HYPOTHESIS_DECISIONS.csv` H-S2 = 0.9039.
* 44.95% = paired mean of (E_W01 − E_P02)/E_W01 — matches `stage8u_results.json`
  H_U3.mean = 0.4495.
* 87.9% = 1 − 139,712 / 1,158,562 = 0.8794 — matches.
* 19.3% = 1 − 9.898e-5 / 1.2272e-4 = 0.1936 — matches.
* 67.70% = 163.67 / 241.75 — matches H-U2 = 0.6770.

No number was inserted without a comparator; no forbidden mapping (e.g. "90% of PoW",
"55% versus Bitcoin") appears in any red insertion (verified by red-run text scan).
