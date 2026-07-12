import { test, expect } from "@playwright/test";
import * as fs from "fs";
import { createZip } from "./helpers/zip";
import { login } from "./helpers/auth";

const BASE = process.env.PLAYWRIGHT_BASE_URL || "https://localhost";

const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "admin@epibridge.local";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin";

const ANALYSIS_CODE = `\
import pandas as pd
df = pd.read_csv("/data/mexico_dengue_2026/demo.csv")
result = df.describe()
result.to_csv("/output/summary.csv")
print(f"Validation: {len(df)} rows processed, {len(df.columns)} columns")
`;

test("Validation Workflow", async ({ page }) => {
  const TS = Date.now();
  const projectName = `Validation Test ${TS}`;
  const analysisName = `Validation Analysis ${TS}`;

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  // Publish platform terms via API (auto-accepts admin; version 3.0.0 avoids
  // conflict with seed-terms 1.0.0 and canonical 2.0.0)
  await page.request.post(`${BASE}/api/admin/terms/platform`, {
    data: {
      version: "3.0.0",
      title: "EpiBridge Platform Terms of Service",
      content: "## Terms\n\nBy using this platform you agree to these terms.",
    },
  });

  // Navigate to Projects page
  await page.getByRole("link", { name: "Projects" }).click();

  // Create a new project
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.getByPlaceholder("Project name").fill(projectName);
  await page
    .getByPlaceholder("Optional description")
    .fill("Validation workflow test project");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Create" })
    .click();

  // Open the project
  await page.getByText(projectName).click();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  // Open the Resources tab and attach the Mexico dengue data resource
  await page.getByRole("link", { name: "Resources", exact: true }).click();
  await expect(page.getByText("Configure Resources")).toBeVisible();
  await page
    .locator("tr")
    .filter({ hasText: "mex-dengue-2026" })
    .getByRole("button", { name: "Attach" })
    .click();

  // Accept dataset terms if presented
  await expect(
    page.getByText(
      "Mexico Dengue Surveillance 2026 \u2014 Terms of Service",
    ),
  ).toBeVisible({ timeout: 10_000 }).catch(() => {});
  await page
    .getByRole("button", { name: "Acknowledge & Continue" })
    .click()
    .catch(() => {});
  await expect(page.getByText("mex-dengue-2026")).toBeVisible();

  // Open the Analysis tab
  await page.getByRole("link", { name: "Analysis" }).click();
  await expect(page.getByTestId("analysis-heading")).toBeVisible();

  // Create a new Draft Bundle
  await page.getByRole("button", { name: "New Draft Bundle" }).click();

  // Wait for redirect to the bundle workspace
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await expect(page.getByText("Draft \u2014 Editable")).toBeVisible();

  // Rename the draft
  await page.locator('input[type="text"]').first().fill(analysisName);

  // Upload the analysis bundle ZIP via the workspace file upload
  const zipBuffer = createZip([
    { name: "run.py", content: ANALYSIS_CODE },
    { name: "requirements.txt", content: "" },
  ]);
  await page.getByRole("button", { name: "Upload ZIP" }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "analysis-bundle.zip",
    mimeType: "application/zip",
    buffer: zipBuffer,
  });

  // Configure execution settings inline in the workspace
  await page.getByLabel("Environment").selectOption({ label: "Python 3.13" });
  await page.locator("#edit-version-exec").fill("1.0.0");

  // Wait for file listing to load then select entrypoint
  await page.waitForTimeout(1000);
  const entrypointSelect = page
    .locator("select")
    .filter({ has: page.locator('option[value="run.py"]') })
    .first();
  if (await entrypointSelect.isVisible()) {
    await entrypointSelect.selectOption("run.py");
  }

  // Select the data resource for this bundle
  await page.getByText("(mex-dengue-2026)").click();

  // --- Run Validation ---
  await page.getByRole("button", { name: "Run Validation" }).click();

  // Wait for validation to complete (PENDING -> RUNNING -> COMPLETED/FAILED)
  await expect(
    page
      .locator(".card")
      .filter({ hasText: "Validation Run" })
      .getByText(/completed|failed/),
  ).toBeVisible({ timeout: 180_000 });

  // Verify validation completed (not failed)
  await expect(
    page
      .locator(".card")
      .filter({ hasText: "Validation Run" })
      .getByText("completed"),
  ).toBeVisible({ timeout: 180_000 });

  // Verify validation log is visible
  await page.getByRole("button", { name: "View Log" }).click();
  await expect(page.getByText("VALIDATION COMPLETED")).toBeVisible({
    timeout: 10_000,
  });
  await expect(
    page.getByText("Validation: 50 rows processed"),
  ).toBeVisible();

  // Verify output files are listed
  await expect(page.getByText("summary.csv")).toBeVisible();

  // Sign out
  await page.getByRole("button", { name: "Sign out" }).click();
});
