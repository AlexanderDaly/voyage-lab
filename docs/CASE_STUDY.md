# Case study: a deadline changes the cheapest feasible speed

The offshore passage is 989.63 nautical miles long, measured on WGS84. The fictional vessel uses 20 tonnes/day of propulsion fuel at 10 knots plus 2 tonnes/day of auxiliary fuel. Costs are $600/tonne, $12,000/day, and no fixed charge. Departure is 11 September 2026 00:00 UTC; the arrival deadline is 100 hours later.

These results measure an implemented synthetic model. They do not establish empirical fuel accuracy or operational savings.

## Default moving storm

| Speed | Elapsed hours | Fuel tonnes | Modeled cost | Deadline |
| --- | ---: | ---: | ---: | --- |
| 10 kn | 106.49 | 97.61 | $111,811.64 | Late |
| 12 kn | 88.18 | 134.32 | $124,680.58 | On time |
| 14 kn | 75.29 | 178.43 | $144,705.02 | On time |

Twelve knots is the lowest-cost feasible choice among these three candidates. Ten knots consumes less fuel, but fails the arrival constraint. Faster is not automatically better: 14 knots adds about $20,024 of modeled cost versus the 12-knot reference.

## Remove weather dependence

The calm fixture sets currents, wind, and wave height to zero while retaining the same route, vessel, costs, and deadline:

| Speed | Elapsed hours | Fuel tonnes | Modeled cost | Deadline |
| --- | ---: | ---: | ---: | --- |
| 10 kn | 98.96 | 90.72 | $103,910.82 | On time |
| 12 kn | 82.47 | 125.63 | $116,611.03 | On time |
| 14 kn | 70.69 | 167.53 | $135,861.63 | On time |

The 10-knot candidate now meets the deadline. This controlled synthetic comparison illustrates the contribution of weather-dependent progress. It is not evidence that a real weather service or routing product would achieve these differences.

## Numerical convergence

Default moving storm at 12 knots:

| Maximum step | Elapsed seconds | Fuel kg | Cost USD |
| --- | ---: | ---: | ---: |
| 900 s | 317432.8732 | 134321.1325 | 124680.5785 |
| 450 s | 317437.6264 | 134323.1438 | 124682.4455 |
| 225 s | 317440.2652 | 134324.2604 | 124683.4820 |

The first halving changes time, fuel, and cost by approximately 0.00150%; the second difference is smaller. This passes the specified 0.5% acceptance threshold for this case. It does not prove uniform convergence for arbitrary imported environments or a bound on physical model error.

## Correctness and runtime

The independent 240-nautical-mile fixture at 10 knots produces 24 hours, 22 tonnes, $13,200 fuel cost, $12,000 time cost, and $25,200 total. Additional tests address current headings, cross-current feasibility, missing coverage, land crossing, weather direction interpolation, time-dependent sampling, and replay integrity.

The recorded 15-run suite contains five synthetic environments and three speeds. A separate 24-hour deadline case is explicitly late. Core simulation took less than 0.06 seconds per run in the initial measurement on Windows with CPython 3.12.14, an AMD64 Family 25 Model 97 processor, and the locked dependencies. Timings exclude JSON validation, hashing, API serialization, browser rendering, and installation; they are single-run observations, not latency percentiles.

[Machine-readable results](../benchmarks/results.json) include exact figures, platform details, scientific implementation fingerprint, and source revision availability. Reproduce with `uv run --frozen python -m benchmarks.run`. This report was measured during initial implementation before the first Git commit; the scientific source fingerprint identifies the measured code.

## Limits and next experiment

There is no optimizer, empirical accuracy dataset, forecast vintage, uncertainty calibration, or route-safety assessment. The next useful experiment is a bounded constant-speed sweep, checked against exhaustive enumeration and displayed as a fuel/time trade-off frontier. Only after that should a live-data adapter or regional graph solver expand the model.
