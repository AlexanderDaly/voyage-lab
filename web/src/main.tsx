import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { PassageMap } from "./Map";
import { Chart } from "./Chart";
import { KNOT, money, stamp } from "./types";
import type { Bundle, Catalog, Run, Scenario, Vessel } from "./types";
import "./style.css";

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `/api/${path}`,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.map((d: { msg: string }) => d.msg).join("; ") ||
          "The request failed",
    );
  return data;
}
const datetimeInput = (v: string) => new Date(v).toISOString().slice(0, 16);
const statusName: Record<string, string> = {
  completed: "On time",
  deadline_exceeded: "Misses deadline",
  infeasible: "Infeasible",
  missing_coverage: "Missing coverage",
  numerical_failure: "Calculation failed",
};

function App() {
  const [catalog, setCatalog] = useState<Catalog>();
  const [draft, setDraft] = useState<Scenario>();
  const [bundle, setBundle] = useState<Bundle>();
  const [selected, setSelected] = useState(1);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [chart, setChart] = useState<"fuel_kg" | "cost" | "ground_speed_mps">(
    "fuel_kg",
  );
  const upload = useRef<HTMLInputElement>(null);

  const compare = useCallback(async (scenario: Scenario) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const speed = scenario.speed_mps / KNOT;
      if (speed < 8 || speed > 16)
        throw new Error(
          "Choose a baseline between 8 and 16 kn to compare three supported speeds.",
        );
      const next = await api<Bundle>("compare", {
        scenario,
        speeds_mps: [speed - 2, speed, speed + 2].map((s) => s * KNOT),
      });
      setBundle(next);
      setSelected(1);
      setDirty(false);
      return next;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    api<Catalog>("catalog")
      .then((data) => {
        setCatalog(data);
        setDraft(data.scenario);
        return compare(data.scenario);
      })
      .catch((e) => setError(e.message));
  }, [compare]);

  useEffect(() => {
    const context = (
      document as Document & {
        modelContext?: {
          registerTool: (
            tool: unknown,
            options: { signal: AbortSignal },
          ) => Promise<void>;
        };
      }
    ).modelContext;
    if (!context || !draft) return;
    const controller = new AbortController();
    try {
      Promise.resolve(
        context.registerTool(
          {
            name: "compare_voyage_speeds",
            title: "Compare voyage speeds",
            description:
              "Run the visible voyage at a baseline speed and two alternatives, updating the comparison.",
            inputSchema: {
              type: "object",
              properties: {
                baseline_knots: { type: "number", minimum: 8, maximum: 16 },
              },
              required: ["baseline_knots"],
              additionalProperties: false,
            },
            annotations: { readOnlyHint: false, untrustedContentHint: false },
            execute: async (input: unknown) => {
              const value = input as { baseline_knots: number };
              if (
                !value ||
                Object.keys(value).length !== 1 ||
                !Number.isFinite(value.baseline_knots) ||
                value.baseline_knots < 8 ||
                value.baseline_knots > 16
              )
                throw new Error("baseline_knots must be between 8 and 16");
              if (busy) throw new Error("A comparison is already running");
              const next = { ...draft, speed_mps: value.baseline_knots * KNOT };
              const result = await compare(next);
              setDraft(next);
              return result?.runs.map((run) => ({
                speed_knots: run.scenario.speed_mps / KNOT,
                status: run.result.status,
                total_cost: run.result.total_cost,
              }));
            },
          },
          { signal: controller.signal },
        ),
      ).catch(() => {});
    } catch {
      /* Optional browser capability; the visible UI remains available. */
    }
    return () => controller.abort();
  }, [draft, compare, busy]);

  function update(patch: Partial<Scenario>) {
    setDraft((d) => d && { ...d, ...patch });
    setDirty(true);
    setNotice("");
  }
  function vessel(patch: Partial<Vessel>) {
    if (draft) update({ vessel: { ...draft.vessel, ...patch } });
  }
  async function changeFixture(name: string) {
    setBusy(true);
    setError("");
    try {
      update({ environment: await api(`fixtures/${name}`) });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function importFile(file?: File) {
    if (!file) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (file.size > 5_000_000)
        throw new Error("Choose a JSON export smaller than 5 MB.");
      const saved = JSON.parse(await file.text());
      const verified = await api<{ verified: boolean; bundle: Bundle }>(
        "replay",
        saved,
      );
      setBundle(verified.bundle);
      setSelected(0);
      setDraft(verified.bundle.runs[0].scenario);
      setDirty(false);
      setNotice(
        `Replay verified · ${verified.bundle.runs.length} runs recomputed from embedded inputs.`,
      );
    } catch (e) {
      setError(`Import failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
      if (upload.current) upload.current.value = "";
    }
  }
  function exportFile() {
    if (!bundle) return;
    const blob = new Blob([JSON.stringify(bundle)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "voyage-lab-comparison.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setNotice("Comparison exported with all inputs for offline replay.");
  }
  const active = bundle?.runs[selected];
  const r = active?.result;
  const displayedRoute = useMemo(
    () =>
      active?.result.completed
        ? {
            ...active.scenario.route,
            coordinates: active.result.trajectory.map(
              (p) => [p.lon, p.lat] as [number, number],
            ),
          }
        : (active?.scenario.route ?? draft?.route),
    [active, draft?.route],
  );
  const referenceIndex = bundle ? Math.floor(bundle.runs.length / 2) : 0;
  const baseline = bundle?.runs[referenceIndex];
  const best = bundle?.runs
    .filter((run) => run.result.deadline_met)
    .reduce<
      Run | undefined
    >((a, b) => (!a || b.result.total_cost < a.result.total_cost ? b : a), undefined);
  const routes = catalog?.routes ?? [];
  return (
    <>
      <header className="topbar">
        <a className="brand" href="/">
          <span className="brand-symbol">V</span> VOYAGE LAB{" "}
          <span className="version">/ 0.1</span>
        </a>
        <span className="top-context">OFFSHORE SIMULATION WORKBENCH</span>
        <span className="offline-badge">Offline fixtures</span>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <div className="eyebrow">EXPERIMENT 001 / US WEST COAST</div>
            <h1>Every knot changes the voyage.</h1>
          </div>
          <div className="file-actions">
            <input
              ref={upload}
              type="file"
              accept=".json,application/json"
              aria-label="Import comparison JSON"
              className="file-input"
              onChange={(e) => void importFile(e.target.files?.[0])}
            />
            <button onClick={() => upload.current?.click()} disabled={busy}>
              Import & replay
            </button>
            <button onClick={exportFile} disabled={!bundle || busy}>
              Export JSON <span aria-hidden>↗</span>
            </button>
          </div>
        </div>
        {error && (
          <div className="message error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="message success" role="status">
            {notice}
          </div>
        )}
        {!draft || !catalog ? (
          <div className="loading">
            {error
              ? "The workbench could not load. Check that the local API is running."
              : "Loading the saved passage…"}
          </div>
        ) : (
          <>
            <div className="workbench">
              <form
                className="controls panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  void compare(draft).catch(() => {});
                }}
              >
                <fieldset disabled={busy}>
                  <div className="section-title">
                    <span className="section-number">01</span>
                    <h2>Define the passage</h2>
                  </div>
                  <label>
                    Offshore route
                    <select
                      value={draft.route.id}
                      onChange={(e) =>
                        update({
                          route: routes.find((x) => x.id === e.target.value)!,
                        })
                      }
                    >
                      {!routes.some((x) => x.id === draft.route.id) && (
                        <option value={draft.route.id}>
                          {draft.route.name} (imported)
                        </option>
                      )}
                      {routes.map((x) => (
                        <option key={x.id} value={x.id}>
                          {x.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="route-caption">
                    Seattle approach → Los Angeles approach
                    <br />
                    Offshore gates only · Harbor transit excluded
                  </div>
                  <label>
                    Departure <span>UTC</span>
                    <input
                      type="datetime-local"
                      required
                      value={datetimeInput(draft.departure)}
                      onChange={(e) =>
                        e.target.value &&
                        update({ departure: e.target.value + ":00Z" })
                      }
                    />
                  </label>
                  <label>
                    Arrival deadline <span>UTC</span>
                    <input
                      type="datetime-local"
                      required
                      value={datetimeInput(draft.deadline)}
                      onChange={(e) =>
                        e.target.value &&
                        update({ deadline: e.target.value + ":00Z" })
                      }
                    />
                  </label>
                  <label>
                    Baseline speed <span>knots through water</span>
                    <div className="speed-control">
                      <input
                        aria-label="Baseline speed"
                        type="number"
                        step="0.5"
                        min="8"
                        max="16"
                        required
                        value={+(draft.speed_mps / KNOT).toFixed(2)}
                        onChange={(e) =>
                          update({ speed_mps: +e.target.value * KNOT })
                        }
                      />
                      <span>± 2 kn comparison</span>
                    </div>
                  </label>
                  <label>
                    Environmental fixture
                    <select
                      value={draft.environment.id}
                      onChange={(e) => void changeFixture(e.target.value)}
                    >
                      {!catalog.fixtures.some(
                        (x) => x.id === draft.environment.id,
                      ) && (
                        <option value={draft.environment.id}>
                          {draft.environment.name} (imported)
                        </option>
                      )}
                      {catalog.fixtures.map((x) => (
                        <option key={x.id} value={x.id}>
                          {x.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="coverage">
                    Synthetic coverage
                    <br />
                    {stamp(draft.environment.times[0])}
                    <br />
                    to {stamp(draft.environment.times.at(-1)!)}
                  </div>
                  <div className="cost-inputs">
                    <label>
                      Fuel <span>USD / tonne</span>
                      <input
                        type="number"
                        required
                        min="0"
                        max="20000"
                        step="10"
                        value={draft.fuel_price_per_kg * 1000}
                        onChange={(e) =>
                          update({ fuel_price_per_kg: +e.target.value / 1000 })
                        }
                      />
                    </label>
                    <label>
                      Time cost <span>USD / day</span>
                      <input
                        type="number"
                        required
                        min="0"
                        max="1000000"
                        step="100"
                        value={draft.daily_cost}
                        onChange={(e) =>
                          update({ daily_cost: +e.target.value })
                        }
                      />
                    </label>
                  </div>
                  <details>
                    <summary>Vessel & model settings</summary>
                    <p className="small">
                      Meridian · fictional cargo vessel. All performance
                      coefficients are synthetic.
                    </p>
                    <label>
                      Reference speed <span>knots</span>
                      <input
                        type="number"
                        required
                        min="6"
                        max="18"
                        step="0.5"
                        value={
                          +(draft.vessel.reference_speed_mps / KNOT).toFixed(2)
                        }
                        onChange={(e) =>
                          vessel({
                            reference_speed_mps: +e.target.value * KNOT,
                          })
                        }
                      />
                    </label>
                    <label>
                      Reference propulsion fuel <span>tonnes / day</span>
                      <input
                        type="number"
                        required
                        min="0.1"
                        max="864"
                        step="0.1"
                        value={
                          +(draft.vessel.reference_fuel_kg_s * 86.4).toFixed(2)
                        }
                        onChange={(e) =>
                          vessel({
                            reference_fuel_kg_s: +e.target.value / 86.4,
                          })
                        }
                      />
                    </label>
                    <label>
                      Auxiliary fuel <span>tonnes / day</span>
                      <input
                        type="number"
                        required
                        min="0"
                        max="432"
                        step="0.1"
                        value={
                          +(draft.vessel.auxiliary_fuel_kg_s * 86.4).toFixed(2)
                        }
                        onChange={(e) =>
                          vessel({
                            auxiliary_fuel_kg_s: +e.target.value / 86.4,
                          })
                        }
                      />
                    </label>
                    <label>
                      Fixed costs <span>USD</span>
                      <input
                        type="number"
                        min="0"
                        max="10000000"
                        value={draft.fixed_cost}
                        onChange={(e) =>
                          update({ fixed_cost: +e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Maximum wave height <span>m · experimental</span>
                      <input
                        type="number"
                        min="0.1"
                        max="30"
                        step="0.1"
                        value={draft.max_wave_m}
                        onChange={(e) =>
                          update({ max_wave_m: +e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Integration step
                      <select
                        value={draft.max_step_s}
                        onChange={(e) =>
                          update({ max_step_s: +e.target.value })
                        }
                      >
                        <option value="900">15 minutes</option>
                        <option value="450">7.5 minutes</option>
                        <option value="225">3.75 minutes</option>
                      </select>
                    </label>
                  </details>
                  <button className="primary" type="submit">
                    {busy ? "Calculating…" : "Compare three speeds"}{" "}
                    <span aria-hidden>→</span>
                  </button>
                </fieldset>
              </form>
              <section className="map-section" aria-label="Voyage map">
                <PassageMap
                  routes={routes}
                  selected={displayedRoute ?? draft.route}
                  land={active?.scenario.land ?? draft.land}
                />
                <div className="map-bottom">
                  <span>
                    <strong>
                      {r ? (r.route_distance_m / 1852).toFixed(0) : "—"}
                    </strong>{" "}
                    nautical miles
                  </span>
                  <span>{active?.scenario.route.name ?? draft.route.name}</span>
                  <span>WGS84</span>
                </div>
              </section>
              <section className="comparison panel">
                <div className="section-title">
                  <span className="section-number">02</span>
                  <h2>Compare the outcomes</h2>
                </div>
                <p className="small">
                  Same vessel, route, and weather snapshot. Each speed
                  encounters weather at its own arrival time.
                </p>
                {dirty && (
                  <div className="stale" role="status">
                    Inputs changed · Compare to update results
                  </div>
                )}
                <div className="scenario-list" aria-label="Speed scenarios">
                  {bundle?.runs.map((run, i) => {
                    const result = run.result;
                    const isBest = best === run;
                    return (
                      <button
                        key={i}
                        className={`scenario-card ${selected === i ? "selected" : ""}`}
                        onClick={() => setSelected(i)}
                        aria-pressed={selected === i}
                        aria-label={`Select ${(run.scenario.speed_mps / KNOT).toFixed(0)} knot scenario`}
                      >
                        <div className="scenario-top">
                          <span className="speed-value">
                            {(run.scenario.speed_mps / KNOT).toFixed(1)}{" "}
                            <small>kn</small>
                          </span>
                          <span
                            className={`status ${result.deadline_met ? "on-time" : "late"}`}
                          >
                            {statusName[result.status]}
                          </span>
                        </div>
                        <div className="scenario-numbers">
                          <strong>
                            {result.completed
                              ? money(result.total_cost)
                              : "Incomplete"}
                          </strong>
                          <span>
                            {(result.elapsed_s / 3600).toFixed(1)} h <b>·</b>{" "}
                            {(result.fuel_kg / 1000).toFixed(1)} t
                          </span>
                        </div>
                        <div className="scenario-footer">
                          <span>
                            {i === referenceIndex
                              ? "REFERENCE"
                              : i < referenceIndex
                                ? "SLOWER"
                                : "FASTER"}
                          </span>
                          {isBest && (
                            <span className="best">Lowest feasible cost</span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
                {bundle && !best && (
                  <p className="constraint-note">
                    No compared scenario meets all constraints. Try a later
                    deadline or different assumptions.
                  </p>
                )}
                {active && (
                  <div className="selected-details">
                    <div className="eyebrow">SELECTED ARRIVAL</div>
                    <strong>{stamp(r!.eta)}</strong>
                    <p className="small">
                      {active.scenario.environment.name} · Synthetic vessel
                    </p>
                    {r!.violation && (
                      <p className="constraint-note">
                        {typeof r!.violation === "string"
                          ? r!.violation
                          : r!.violation.message}
                      </p>
                    )}
                    {baseline && r!.completed && baseline.result.completed && (
                      <p className="savings">
                        {money(baseline.result.total_cost - r!.total_cost)}{" "}
                        savings vs reference
                      </p>
                    )}
                  </div>
                )}
              </section>
            </div>
            {active && r && (
              <section className="analysis-panel panel">
                <div className="analysis-header">
                  <div className="section-title">
                    <span className="section-number">03</span>
                    <h2>Inside the selected voyage</h2>
                    <span className="analysis-speed">
                      {(active.scenario.speed_mps / KNOT).toFixed(1)} kn
                    </span>
                  </div>
                  <label className="chart-picker">
                    Show
                    <select
                      aria-label="Chart metric"
                      value={chart}
                      onChange={(e) => setChart(e.target.value as typeof chart)}
                    >
                      <option value="fuel_kg">Cumulative fuel</option>
                      <option value="cost">Cumulative cost</option>
                      <option value="ground_speed_mps">Ground speed</option>
                    </select>
                  </label>
                </div>
                <div className="analysis-content">
                  <Chart
                    points={r.trajectory}
                    field={chart}
                    label={
                      chart === "fuel_kg"
                        ? "Fuel consumed"
                        : chart === "cost"
                          ? "Modeled cost"
                          : "Speed over ground"
                    }
                    unit={
                      chart === "fuel_kg"
                        ? "tonnes"
                        : chart === "cost"
                          ? "USD"
                          : "knots"
                    }
                    scale={
                      chart === "fuel_kg"
                        ? 0.001
                        : chart === "ground_speed_mps"
                          ? 1 / KNOT
                          : 1
                    }
                  />
                  <Chart
                    points={r.trajectory}
                    field="wave_height_m"
                    label="Waves encountered"
                    unit="metres"
                    color="#9c652b"
                  />
                  <div className="cost-ledger">
                    <div>
                      <span>Fuel</span>
                      <strong>{money(r.fuel_cost)}</strong>
                    </div>
                    <div>
                      <span>Time</span>
                      <strong>{money(r.time_cost)}</strong>
                    </div>
                    <div>
                      <span>Fixed</span>
                      <strong>{money(r.fixed_cost)}</strong>
                    </div>
                    <div className="total">
                      <span>
                        {r.completed ? "Total modeled cost" : "Partial cost"}
                      </span>
                      <strong>{money(r.total_cost)}</strong>
                    </div>
                    <span className="small">
                      Gate to gate · USD
                      <br />
                      No port waiting or harbor fuel
                    </span>
                  </div>
                </div>
              </section>
            )}
            <footer>
              <p>
                <strong>A transparent model, with limits.</strong> Fictional
                vessel performance and synthetic weather. Research and portfolio
                use only; this workbench does not validate navigation, vessel
                safety, or commercial fuel estimates.
              </p>
              <span>
                Python scientific core
                <br />
                Reproducible by design
              </span>
            </footer>
          </>
        )}
      </main>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
