# Stage 9 — Expected Examiner Questions and Answers

1. Why is 90.39% not a comparison with PoW? It is retention vs the NO-FLOOR PoCol control (S00), an internal baseline; it measures how much throughput the operating policy preserves within PoCol, not against PoW.
2. Why is 55.05% not a hardware measurement? It is a calculated low-power-state energy difference vs the within-run power-null reference on the same event path, from the instrumented simulator's residency accounting.
3. Why does matched PoW produce more blocks? Every uncoordinated PoW node searches the whole domain, so the first valid solution is found sooner; PoCol serialises a round behind the single miner owning the winning nonce.
4. Why does PoCol evaluate fewer nonces? Disjoint allocation removes exact-input duplication; matched PoW duplicates ~942k of ~1.16M evaluations.
5. Why are duplicate-input results not directly generalisable to Bitcoin? Real PoW headers vary per miner (extranonce, coinbase, timestamp); the duplicate-elimination result holds under the modelled common immutable template, not real header diversity.
6. Why did the joint operational claims fail? The useful-floor duration and the service/latency gates were not met at the reduced scale (reserve wakes cannot pay for themselves; partitioned search lengthens rounds).
7. Why is the thesis still a valid doctoral contribution? A complete protocol, a rigorous preregistered evaluation framework, and a quantified, honestly-bounded trade-off with negative results are a genuine scientific contribution; a null/partial result reported with integrity is doctoral-quality.
8. What remains unproven about security and incentives? Common-prefix, chain-quality, Sybil-resistance and incentive-compatibility are not formally proven; the operational floor is an engineering target.
9. Why were reduced-scale experiments used? To make preregistered, checksum-frozen, exactly-reproducible confirmatory runs tractable while retaining the accepted work semantics.
10. What is the practical meaning of the energy-service trade-off? PoCol buys large energy and work-efficiency gains at the cost of longer rounds and fewer blocks per horizon; it suits energy-constrained settings that tolerate higher latency, not throughput-maximising ones.
