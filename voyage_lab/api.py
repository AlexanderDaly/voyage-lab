"""Local FastAPI service. Built React assets share the same origin."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .fixtures import FIXTURES, ROUTES, default_scenario, load_environment
from .models import CompareRequest, ExportBundle, Scenario, Vessel
from .replay import export_run, replay, source_revision

app = FastAPI(
    title="Voyage Lab", version="0.1.0", description="Synthetic offshore voyage research; not navigation"
)
MAX_BODY = 5_000_000


@app.middleware("http")
async def bounded_body(request: Request, call_next):
    if request.method == "POST":
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BODY:
                return JSONResponse(status_code=413, content={"detail": "JSON upload exceeds 5 MB"})
            chunks.append(chunk)
        request._body = b"".join(chunks)
    return await call_next(request)


@app.exception_handler(ValidationError)
async def validation_error(_request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def invalid_request(_request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0", "environment": "offline synthetic"}


@app.get("/api/catalog")
def catalog():
    scenario = default_scenario()
    return {
        "scenario": scenario,
        "routes": ROUTES,
        "fixtures": [{"id": key, "name": name} for key, name in FIXTURES.items()],
    }


@app.get("/api/vessels")
def vessels():
    return [Vessel()]


@app.get("/api/routes")
def routes():
    return ROUTES


@app.get("/api/fixtures/{name}")
def fixture(name: str):
    if name not in FIXTURES:
        raise HTTPException(404, "Unknown environmental fixture")
    return load_environment(name)


@app.post("/api/simulate")
def simulate_api(scenario: Scenario):
    return export_run(scenario)


@app.post("/api/compare")
def compare(request: CompareRequest):
    revision = source_revision()
    # Validate every scenario before starting any calculation.
    scenarios = [
        Scenario.model_validate(request.scenario.model_dump() | {"speed_mps": speed})
        for speed in request.speeds_mps
    ]
    return ExportBundle(runs=[export_run(s, revision) for s in scenarios])


@app.post("/api/replay")
def replay_api(bundle: ExportBundle):
    return {"verified": True, "bundle": replay(bundle)}


@app.get("/api/land")
def land():
    return {"type": "Feature", "properties": {}, "geometry": default_scenario().land}


DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
