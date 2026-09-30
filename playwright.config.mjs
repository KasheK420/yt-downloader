import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: "http://127.0.0.1:8765", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command:
      process.platform === "win32"
        ? ".venv\\Scripts\\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log"
        : ".venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log",
    url: "http://127.0.0.1:8765/healthz",
    reuseExistingServer: false,
    env: { YTD_DATA_DIR: ".local/browser-data" },
  },
});
