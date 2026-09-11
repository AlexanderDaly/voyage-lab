"""One-time acquisition. Runtime and tests use the checked-in regional asset."""

import hashlib
import json
import urllib.request
from pathlib import Path

from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_land.geojson"


def main():
    raw = urllib.request.urlopen(URL, timeout=60).read()
    data = json.loads(raw)
    bounds = box(-130, 30, -116, 50)
    land = unary_union(
        [
            shape(f["geometry"]).intersection(bounds)
            for f in data["features"]
            if shape(f["geometry"]).intersects(bounds)
        ]
    )
    dest = ROOT / "voyage_lab" / "data"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "land.geojson").write_text(json.dumps(mapping(land), separators=(",", ":")), encoding="utf-8")
    (dest / "land-provenance.json").write_text(
        json.dumps(
            {
                "source": URL,
                "version": "Natural Earth 5.1.2 / 1:50m land",
                "license": "Public domain",
                "terms": "https://www.naturalearthdata.com/about/terms-of-use/",
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "transform": "Clip to WGS84 [-130,30,-116,50]; union; no simplification",
                "warning": "Coarse research mask; not a navigational chart or safety validation",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved {dest / 'land.geojson'} ({(dest / 'land.geojson').stat().st_size} bytes)")


if __name__ == "__main__":
    main()
