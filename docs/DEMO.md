# Two-minute walkthrough

1. **0:00–0:20 — Open the workbench.** Point out the offshore gates, synthetic vessel/weather labels, and fixed UTC dates. This is an experiment, not a navigation recommendation.
2. **0:20–0:45 — Compare the default speeds.** At 10 knots the voyage consumes less fuel but arrives after the deadline. Twelve knots is the least expensive on-time option among these three candidates. Fourteen knots arrives sooner at greater modeled cost.
3. **0:45–1:10 — Inspect the calculation.** Select a scenario and show the waves encountered, cumulative fuel, and cost breakdown. Explain the cubic propulsion assumption and why changing speed changes the weather encountered.
4. **1:10–1:30 — Change an assumption.** Choose calm water or extend the deadline, then compare again. The highlighted result follows the changed assumptions.
5. **1:30–1:50 — Export and replay.** Export JSON, reload, and import it. The app recomputes every trajectory sample from the embedded input data before confirming verification.
6. **1:50–2:00 — Show the evidence.** Open the hand-calculated test and measured convergence table. State the limits: no calibrated fuel model, live forecasts, regional optimizer, or navigation validation.

This is a script for a future recording; no video has been recorded yet.
