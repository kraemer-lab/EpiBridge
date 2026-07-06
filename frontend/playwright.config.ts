import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 300_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "https://localhost",
    ignoreHTTPSErrors: true,
  },
});
