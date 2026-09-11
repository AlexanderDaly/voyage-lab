# Contributing

Use the setup and verification commands in README.md. Keep numerical code in `voyage_lab/core.py` independent of I/O and UI concerns. Include an independent expected answer or failure-mode test for changes to scientific behavior.

Use SI internally, WGS84 `[longitude, latitude]`, and aware UTC timestamps. State direction conventions in adapter code. Do not turn missing fields into zero-valued weather. Preserve the distinction between an invalid request, incomplete physical transition, coverage failure, numerical failure, and a completed late voyage.

Changing a scientific formula or replay contract requires a model/schema version decision, updated documentation, and regenerated benchmark evidence. Do not claim calibrated fuel estimates or route safety from synthetic tests. Every dataset needs provenance and redistribution terms.

Keep changes scoped to this repository. Do not commit credentials, personal exports, generated environments, node_modules, browser traces, or downloaded global datasets. CI runs the same checks documented locally; a change is ready when those checks pass and any unverified platform behavior is explicitly stated.
