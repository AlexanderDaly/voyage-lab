export type Land =
  | { type: "Polygon"; coordinates: number[][][] }
  | { type: "MultiPolygon"; coordinates: number[][][][] };
export type Route = {
  id: string;
  name: string;
  coordinates: [number, number][];
};
export type Environment = {
  id: string;
  name: string;
  kind: "synthetic";
  times: string[];
  fields: Record<string, number[][][]>;
  [key: string]: unknown;
};
export type Vessel = {
  name: string;
  reference_speed_mps: number;
  reference_fuel_kg_s: number;
  auxiliary_fuel_kg_s: number;
  min_speed_mps: number;
  max_speed_mps: number;
  [key: string]: unknown;
};
export type Scenario = {
  name: string;
  departure: string;
  deadline: string;
  speed_mps: number;
  fuel_price_per_kg: number;
  daily_cost: number;
  fixed_cost: number;
  max_step_s: number;
  max_wave_m: number;
  currency: "USD";
  vessel: Vessel;
  route: Route;
  environment: Environment;
  land: Land;
};
export type Point = {
  time: string;
  elapsed_s: number;
  lon: number;
  lat: number;
  distance_m: number;
  fuel_kg: number;
  cost: number;
  ground_speed_mps: number;
  wave_height_m: number;
};
export type Result = {
  status: string;
  violation: string | { code: string; message: string } | null;
  completed: boolean;
  deadline_met: boolean;
  elapsed_s: number;
  distance_m: number;
  route_distance_m: number;
  eta: string | null;
  fuel_kg: number;
  total_cost: number;
  fuel_cost: number;
  time_cost: number;
  fixed_cost: number;
  trajectory: Point[];
};
export type Run = {
  scenario: Scenario;
  result: Result;
  hashes: Record<string, string>;
  model_version: string;
  source_revision: string;
  schema_version: string;
};
export type Bundle = { bundle_version: "1.0"; runs: Run[] };
export type Catalog = {
  scenario: Scenario;
  routes: Route[];
  fixtures: { id: string; name: string }[];
};
export const KNOT = 1852 / 3600;
export const money = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
export const stamp = (v: string | null) =>
  v
    ? new Date(v).toLocaleString("en-US", {
        timeZone: "UTC",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }) + " UTC"
    : "Not reached";
