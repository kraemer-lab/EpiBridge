import { test, expect } from "@playwright/test";
import fs from "fs";

test("Golden Path: researcher runs analysis and downloads output", async ({ page }) => {
  // 1. Open EpiBridge
  await page.goto("/");

  // 2. Logged in automatically via dev auth — verify header shows user
  await expect(page.getByText("Administrator")).toBeVisible();

  // 3. Navigate to Projects page
  await page.getByRole("link", { name: "Projects" }).click();

  // 4. Open the demo project — wait for project page to render
  await page.getByText("Dengue Analysis Demo").click();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  // 5. Open the Analysis tab — wait for page to load
  await page.getByRole("link", { name: "Analysis" }).click();
  await expect(page.getByText("Analysis Bundles")).toBeVisible();

  // 6. Select the demo analysis
  await page.getByText("Dengue Summary Statistics").click();

  // 7. Click Run Analysis
  await page.getByRole("button", { name: "Run Analysis" }).click();

  // 8. Wait for the Execution Request to transition: PENDING → RUNNING → COMPLETED
  await expect(page.getByText("completed").first()).toBeVisible({ timeout: 180_000 });

  // 9. Open the Outputs tab
  await page.getByRole("link", { name: "Outputs" }).click();

  // 10. Download summary.csv
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download" }).first().click(),
  ]);

  // 11. Verify that the downloaded file exists and is non-empty
  expect(download.suggestedFilename()).toBe("summary.csv");
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  if (downloadPath) {
    const stats = fs.statSync(downloadPath);
    expect(stats.size).toBeGreaterThan(0);
  }
});
