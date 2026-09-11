# Voyage Lab status

Updated: 11 September 2026. Local v0.1 implementation is complete. GitHub publication awaits the user's requested final confirmation.

## Completed

- Original Python scientific package, validated SI scenario models, CLI, and FastAPI service.
- WGS84 geodesic progress, whole-edge land intersections, vector currents, track-holding feasibility, and synthetic wind/wave losses.
- Time-dependent interpolation with explicit spatial/time coverage, shortened integration steps, bounded runtime, and separate failure outcomes.
- Five bundled synthetic fixtures and two curated tracks in one offshore corridor; no harbor navigation.
- React/TypeScript interface, entirely local MapLibre map, three-speed comparisons, charts, selected-run assumptions, and cost breakdown.
- JSON import/export that embeds every input dependency and recomputes all trajectory and result values.
- Python/frontend lockfiles, native Windows setup, CLI wheel packaging, tests, CI workflow, MIT license, notices, model documentation, measured case study, and demo walkthrough script.

## Verification evidence

| Check | Observed result |
| --- | --- |
| Python scientific/API suite | **35 passed**, Windows CPython 3.12.14 |
| Ruff lint and formatting check | Passed |
| Python lockfile consistency | `uv lock --check --offline` passed |
| Frontend TypeScript and production build | Passed, Node 24.19.0 / pnpm 11.19.0 |
| Chromium end-to-end tests | **3 passed**: complete comparison/export/replay, errors/alternate route, mobile layout |
| Offline browser workflow | All external HTTP requests blocked; zero external requests observed |
| Installed Python wheel | Built, installed into a separate virtual environment, and replayed all three runs with `python -I` |
| Network-disabled installed replay | `scripts/verify_installed.py` blocks socket connection/DNS functions and verifies installed fixtures plus numerical replay; passed |
| Numerical fixture | 240 nm / 10 kn = 24 h, 22 t fuel, $25,200 total |
| Convergence | 900→450 s changes default metrics by approximately 0.00150%; further halving reduces the difference |
| Benchmark | 15 measured core runs plus convergence and tight-deadline cases; initial maximum below 0.06 s |
| Visual review | Desktop map, scenarios, and charts inspected; mobile overflow checked at 390 px |
| Structured browser action | Valid input updated the visible comparison; 30-kn input rejected with the baseline unchanged |

See `benchmarks/results.json` for exact measurements. Browser test traces and local exports remain ignored. `docs/workbench.png` is a screenshot of the tested default example.

## Known limitations

- Synthetic physics and environment, coarse land mask, constant speeds, USD only. No forecast, calibrated accuracy, full optimizer, navigation validation, or probabilistic arrival claim.
- Only Windows execution is verified locally. Ubuntu CI and cross-platform replay remain unverified until GitHub Actions runs.
- Two upstream test-client deprecation warnings occur with the locked FastAPI/Starlette stack; no test failures.
- Vite reports a large bundle warning because MapLibre is included. The production JS is approximately 1.30 MB before compression / 361 KB gzip; it is served locally with no external assets.
- The wheel contains the CLI/API and scientific fixtures. The React application is built from the repository; the wheel alone does not contain the compiled frontend.
- The browser keeps comparisons in memory. Export before closing. No recorded video exists; a two-minute walkthrough script is provided.
- Initial benchmark source revision is unavailable because it was measured before the first commit. Its scientific source fingerprint is recorded.

## Publication and next task

Authenticated connected GitHub account and Git credential-manager account: `AlexanderDaly`. Preferred repository: `voyage-lab`, proposed public visibility for the portfolio. A repository metadata check returned 404; creation must recheck the name at publication time. No remote is configured and nothing has been published.

Publication contents: source, fixtures, regional public-domain land subset and provenance, test suites, lockfiles, documentation, screenshot, MIT license, and CI. Exclude local environments, exports, node_modules, generated builds, credentials, and browser traces.

Publication audit: 56 intended tracked files, approximately 703 KB. Targeted private-key/token/personal-path patterns produced no matches; no excluded generated directories or files above 2 MB were tracked. This is a scoped scan plus file-list review, not a guarantee that arbitrary future changes contain no secrets.

**Next concrete task:** obtain confirmation for public publication to `AlexanderDaly/voyage-lab`, create the repository without overwriting any existing remote, push the prepared commit, inspect CI, and fix project-caused failures. Then consider a bounded speed-sweep experiment.
