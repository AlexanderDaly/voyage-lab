# Weather Routing Tool feasibility assessment

Assessment date: 11 September 2026. This was a source/configuration review, not an installation or reproduced upstream experiment.

52°North's [Weather Routing Tool](https://github.com/52North/WeatherRoutingTool) is an MIT-licensed Python routing project and a plausible future comparison backend. Its [configuration template](https://github.com/52North/WeatherRoutingTool/blob/main/config.template.json) defines departure, route/map bounds, vessel parameters, weather/depth file paths, and routing constraints. Its [dependency list](https://github.com/52North/WeatherRoutingTool/blob/main/requirements.txt) includes a larger geospatial, data, and optimization stack than the standalone v0.1 needs.

**Decision:** preserve the standalone forward simulator and defer integration. Next spike: pin an upstream commit, reproduce one documented example in an isolated environment, record exact environmental/vessel inputs, and export its route geometry and metrics. Reevaluate the route with Voyage Lab using clearly matched assumptions; do not compare fuel savings across unmatched vessel models.

Proposed adapter inputs: versioned scenario, immutable environment snapshot, vessel mapping, supported constraints, and bounded solver configuration. Outputs: WGS84 track, time/speed plan, upstream diagnostics, source revision, and provenance. Feed any route back through the standalone forward model for comparison.

The upstream configuration uses its own coordinate/parameter conventions; an adapter must translate explicitly. Availability of an example was not established by execution in this milestone. No upstream code was copied or vendored, and no benchmark result here comes from WRT.
