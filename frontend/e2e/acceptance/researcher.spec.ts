import { test, expect } from "@playwright/test";
import { createZip } from "../helpers/zip";
import { login } from "../helpers/auth";
import {
  RESEARCHER_EMAIL,
  RESOURCE_IDENTIFIER,
  ensureTermsPublished,
  provisionProject,
} from "../helpers/setup";

const ANALYSIS_CODE = `\
import pandas as pd
df = pd.read_csv("/data/demo-surveillance/demo.csv")
summary = df.describe()
summary.to_csv("/output/summary.csv")
print(f"Processed {len(df)} rows.")
`;

test("Researcher Acceptance", async ({ page }) => {
  const TS = Date.now();
  const analysisName = `Analysis ${TS}`;

  await ensureTermsPublished();
  const project = await provisionProject(TS, RESEARCHER_EMAIL);

  await login(page, RESEARCHER_EMAIL, "researcher");
  await expect(page.getByTestId("header-user-name")).toBeVisible();

  await page.getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByText(project.name).click();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  await page.getByRole("link", { name: "Analysis" }).click();
  await expect(page.getByTestId("analysis-heading")).toBeVisible();
  await page.getByRole("button", { name: "New Draft Bundle" }).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await expect(page.getByText("Draft \u2014 Editable")).toBeVisible();

  await page.locator('input[type="text"]').first().fill(analysisName);

  const zipBuffer = createZip([
    { name: "run.py", content: ANALYSIS_CODE },
    { name: "requirements.txt", content: "" },
  ]);
  await page.getByRole("button", { name: "Upload ZIP" }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "bundle.zip",
    mimeType: "application/zip",
    buffer: zipBuffer,
  });

  await page.getByLabel("Environment").selectOption({ label: "Python 3.13" });
  await page.locator("#edit-version-exec").fill("1.0.0");

  await page.waitForTimeout(1000);
  const entrypointSelect = page
    .locator("select")
    .filter({ has: page.locator('option[value="run.py"]') })
    .first();
  if (await entrypointSelect.isVisible()) {
    await entrypointSelect.selectOption("run.py");
  }
  await page.getByLabel("Interpreter").selectOption("Python");
  await page.getByText(`(${RESOURCE_IDENTIFIER})`).click();

  await page.getByRole("button", { name: "Run Validation" }).click();
  await expect(
    page.locator(".card").filter({ hasText: "Validation Run" }).getByText(/completed/),
  ).toBeVisible({ timeout: 180_000 });

  await page.getByRole("button", { name: "View Log" }).click();
  await expect(page.getByText("VALIDATION COMPLETED")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("50 rows")).toBeVisible();

  await page.getByRole("button", { name: "Save and Close" }).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis$/);
  await page.getByText(analysisName).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await page.getByRole("button", { name: "Submit for Review" }).click();
  await expect(page.getByText("Submitted")).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
});
