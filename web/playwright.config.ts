import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8000",
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      "uv run --frozen python -m uvicorn voyage_lab.api:app --host 127.0.0.1 --port 8000",
    cwd: "..",
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
  },
});
