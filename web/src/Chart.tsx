import { useId } from "react";
import type { Point } from "./types";

export function Chart({
  points,
  field,
  label,
  unit,
  scale = 1,
  color = "#176a76",
}: {
  points: Point[];
  field: "fuel_kg" | "cost" | "wave_height_m" | "ground_speed_mps";
  label: string;
  unit: string;
  scale?: number;
  color?: string;
}) {
  const id = useId();
  if (!points.length)
    return <div className="chart-empty">No trajectory available</div>;
  const width = 500,
    height = 140,
    left = 46,
    right = 14,
    top = 15,
    bottom = 30;
  const end = Math.max(1, points.at(-1)!.elapsed_s);
  const maximum = Math.max(0.01, ...points.map((p) => p[field] * scale)) * 1.12;
  const x = (t: number) => left + (t / end) * (width - left - right);
  const y = (v: number) =>
    height - bottom - (v / maximum) * (height - top - bottom);
  const path = points
    .map(
      (p, i) =>
        `${i ? "L" : "M"}${x(p.elapsed_s).toFixed(2)},${y(p[field] * scale).toFixed(2)}`,
    )
    .join(" ");
  return (
    <div className="chart">
      <div className="chart-heading">
        <h3>{label}</h3>
        <span>{unit}</span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${label} over voyage elapsed hours`}
      >
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity=".18" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line
              x1={left}
              x2={width - right}
              y1={y(maximum * f)}
              y2={y(maximum * f)}
              stroke="#dde5e8"
            />
            <text x={left - 8} y={y(maximum * f) + 4} textAnchor="end">
              {(maximum * f).toFixed(maximum > 100 ? 0 : 1)}
            </text>
          </g>
        ))}
        <path
          d={`${path} L${x(end)},${y(0)} L${left},${y(0)} Z`}
          fill={`url(#${id})`}
        />
        <path d={path} stroke={color} strokeWidth="2.5" fill="none" />
        {[0, 0.5, 1].map((f) => (
          <text key={f} x={x(end * f)} y={height - 7} textAnchor="middle">
            {((end * f) / 3600).toFixed(0)} h
          </text>
        ))}
      </svg>
    </div>
  );
}
