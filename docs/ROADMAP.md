# Roadmap

## Implemented in v0.1

- SI scientific core, WGS84 geodesic tracks, synthetic vessel and transparent weather loss.
- Current projection and simplified track holding; whole-edge land checks.
- Time-dependent synthetic environment sampling and strict coverage failures.
- Two curated offshore tracks, five fixtures, three-speed comparisons, deadline flags.
- CLI, FastAPI, React/TypeScript workbench, offline MapLibre map, and charts.
- Self-contained export/import with numerical replay and content checks.
- Scientific/API tests, browser workflow tests, measured sensitivity/convergence suite.

## Next: make the experiment stronger

1. Run and inspect CI on Linux after publication; resolve any portability differences.
2. Add a speed sweep with explicit discrete search bounds and a fuel/time trade-off frontier. Compare it against exhaustive small cases before claiming optimization.
3. Add a forecast adapter that preserves exact source responses, issue time, retrieval time, coverage, coordinate conventions, licenses, and hashes. Keep offline replay mandatory.
4. Evaluate WRT using one reproduced example in a separate environment, with a documented mapping into Voyage Lab's scenario/result contract.

## v0.2 research work

Regional graph routing with time-aware states, constrained speed choices, forward revalidation, discretization sensitivity, and transparent optimality claims. Then coherent weather scenarios, forecast-vintage experiments, and better model comparisons.

Empirical fuel/arrival accuracy requires appropriate measured vessel data. Fleet dispatch, real navigation, berth scheduling, AIS ingestion, compliance accounting, and conversational controls remain out of scope.
