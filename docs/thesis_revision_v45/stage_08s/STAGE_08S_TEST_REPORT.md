# Stage 8S — Test Report (implementation gate for COMMIT 1)

Executed locally (no CI): **235 passed** = 195 accepted engine tests + 18 Stage-8R
R-TESTs (all retained, unchanged) + 22 new S8S-TESTs. The frozen Stage-6M byte-identity
gate `test_s6m_08` remains failing-by-construction on refinement branches exactly as
documented since Stage 8R; every Stage-6M/7M/8M/8R evidence manifest still verifies.

| test | proof |
|---|---|
| S8S-TEST-01 | LEGACY_REACTIVE bit-exactly reproduces the frozen Stage-8M M03 record; useful/coarse registries inert |
| S8S-TEST-02 | STAGE8R_PREDICTIVE_STATIC_FLOOR reproduces frozen R02 seed 0: rounds, blocks, seats, batches, below-floor exactly; energy to 1 ULP (pair-vs-accumulator summation order) |
| S8S-TEST-03 | WAKING contributes zero to H_effective |
| S8S-TEST-04 | static floor is exactly 0.80 × H0 in every scenario config and report |
| S8S-TEST-05 | H_useful_target never exceeds the static floor (cap verified with availability ≫ floor) |
| S8S-TEST-06 | a miner with an empty range contributes zero to H_useful_available |
| S8S-TEST-07 | an awake receiver counts only when a donor has a cedable non-overlapping suffix (spare-batch bound 0 → excluded; bound 2 → included) |
| S8S-TEST-08 | coarse chunks pairwise disjoint (every lineage of a full S03 run) |
| S8S-TEST-09 | chunks contiguous and the donor never evaluates inside a ceded chunk (ledger-verified union/exclusion) |
| S8S-TEST-10 | one repartition per donor lineage per episode (single seated_at per lineage; count == lineage count) |
| S8S-TEST-11 | a receiver never holds two live chunks (previous COMPLETED before next seated) |
| S8S-TEST-12 | identical rerun produces identical chunk ids/bounds/receivers (determinism) |
| S8S-TEST-13 | no reserve batch seated in the same decision instant as a coarse repartition |
| S8S-TEST-14 | every reserve wake is bound to a non-empty unclaimed slice; bound-work counter equals seats; rejection counter ↔ rejection log |
| S8S-TEST-15 | every wake request carries exact round/template/slice identity |
| S8S-TEST-16 | zero physical-frontier rewinds (S02 + S03) |
| S8S-TEST-17 | zero duplicate nonces (S02 + S03) |
| S8S-TEST-18 | zero post-round evaluations (accepted Stage-5D audit) |
| S8S-TEST-19 | energy identity ≤ 1e-8 J, residency partition ≤ 1e-9 s |
| S8S-TEST-20 | closure leaves zero live episodes/batches/activation/coarse requests, leases, reassignments |
| S8S-TEST-21 | static and useful floor metrics both present, independently computed, genuinely different |
| S8S-TEST-22 | target and difficulty identical across all seven controller modes |
