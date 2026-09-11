import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Land, Route } from "./types";

export function PassageMap({
  routes,
  selected,
  land,
}: {
  routes: Route[];
  selected: Route;
  land: Land;
}) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!host.current) return;
    try {
      const view = new maplibregl.Map({
        container: host.current,
        attributionControl: false,
        style: {
          version: 8,
          sources: {},
          layers: [
            {
              id: "ocean",
              type: "background",
              paint: { "background-color": "#102e36" },
            },
          ],
        },
        bounds: [
          [-129.2, 32.5],
          [-117, 49.2],
        ],
        fitBoundsOptions: {
          padding: { top: 45, bottom: 48, left: 35, right: 35 },
        },
        maxBounds: [
          [-135, 26],
          [-110, 54],
        ],
        minZoom: 2,
        maxZoom: 9,
      });
      map.current = view;
      view.addControl(
        new maplibregl.NavigationControl({ showCompass: false }),
        "bottom-right",
      );
      view.on("load", () => {
        view.addSource("land", {
          type: "geojson",
          data: { type: "Feature", properties: {}, geometry: land },
        });
        view.addLayer({
          id: "land-fill",
          type: "fill",
          source: "land",
          paint: { "fill-color": "#274750" },
        });
        view.addLayer({
          id: "coast",
          type: "line",
          source: "land",
          paint: { "line-color": "#55717a", "line-width": 1 },
        });
        const features = routes
          .filter((r) => r.id !== selected.id)
          .map((r) => ({
            type: "Feature" as const,
            properties: {},
            geometry: {
              type: "LineString" as const,
              coordinates: r.coordinates,
            },
          }));
        view.addSource("alternates", {
          type: "geojson",
          data: { type: "FeatureCollection", features },
        });
        view.addLayer({
          id: "alternates",
          source: "alternates",
          type: "line",
          paint: {
            "line-color": "#77949c",
            "line-width": 2,
            "line-dasharray": [3, 3],
          },
        });
        view.addSource("selected", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: { type: "LineString", coordinates: selected.coordinates },
          },
        });
        view.addLayer({
          id: "route-glow",
          source: "selected",
          type: "line",
          paint: {
            "line-color": "#d5fa55",
            "line-width": 8,
            "line-opacity": 0.1,
          },
        });
        view.addLayer({
          id: "route",
          source: "selected",
          type: "line",
          paint: { "line-color": "#d5fa55", "line-width": 2.5 },
        });
        for (const [position, text] of [
          [selected.coordinates[0], "Departure offshore gate"],
          [selected.coordinates.at(-1)!, "Arrival offshore gate"],
        ] as const) {
          const el = document.createElement("div");
          el.className = "gate-marker";
          el.textContent = text;
          new maplibregl.Marker({ element: el, anchor: "left" })
            .setLngLat(position)
            .addTo(view);
        }
        for (const [position, text] of [
          [[-122.33, 47.6], "SEATTLE"],
          [[-118.24, 34.05], "LOS ANGELES"],
          [[-122.42, 37.77], "SAN FRANCISCO"],
        ] as const) {
          const el = document.createElement("div");
          el.className = "city-marker";
          el.textContent = text;
          new maplibregl.Marker({ element: el })
            .setLngLat([position[0], position[1]])
            .addTo(view);
        }
      });
      return () => {
        view.remove();
        map.current = null;
      };
    } catch {
      setFailed(true);
    }
  }, [routes, selected, land]);
  return (
    <div className="map-frame">
      <div
        ref={host}
        className="passage-map"
        aria-label="Map of the supported offshore passage"
      />
      <div className="map-caption">
        <span className="map-kicker">NORTH PACIFIC</span>
        <strong>One corridor. Two perspectives.</strong>
      </div>
      <div className="map-legend">
        <span className="line-key" /> Selected track{" "}
        <span className="line-key alternate" /> Alternate
      </div>
      <div className="map-credit">
        Made with Natural Earth · Research geometry, not navigation
      </div>
      {failed && (
        <div className="map-fallback" role="status">
          Map rendering is unavailable. Track coordinates remain in the export.
        </div>
      )}
    </div>
  );
}
