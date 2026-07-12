import { test, expect } from "@playwright/test";
import { createZip } from "./helpers/zip";
import { login } from "./helpers/auth";

const BASE = process.env.PLAYWRIGHT_BASE_URL || "https://localhost";

const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "admin@epibridge.local";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin";

const ANALYSIS_CODE = `\
import pandas as pd
df = pd.read_csv("/data/mexico_dengue_2026/demo.csv")
summary = df.describe()
summary.to_csv("/output/summary.csv")
print(f"Analysis complete. Processed {len(df)} rows, {len(df.columns)} columns.")
`;

const CONFIG_CONTENT = `\
# Analysis configuration
iterations: 1000
threshold: 0.05
output_format: csv
`;

test("Submission Inspection", async ({ page }) => {
  const TS = Date.now();
  const projectName = `Inspection Test ${TS}`;
  const analysisName = `Inspect Analysis ${TS}`;

  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  // Publish platform terms via API
  await page.request.post(`${BASE}/api/admin/terms/platform`, {
    data: {
      version: "2.0.0",
      title: "EpiBridge Platform Terms of Service",
      content: "## Terms\n\nBy using this platform you agree to these terms.",
    },
  });

  // Create a project
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.getByPlaceholder("Project name").fill(projectName);
  await page.getByPlaceholder("Optional description").fill("Submission inspection test project");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();

  // Open the project
  await page.getByText(projectName).click();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  // Attach the Mexico dengue data resource
  await page.getByRole("link", { name: "Resources", exact: true }).click();
  await expect(page.getByText("Configure Resources")).toBeVisible();
  await page
    .locator("tr")
    .filter({ hasText: "mex-dengue-2026" })
    .getByRole("button", { name: "Attach" })
    .click();
  await page.getByRole("button", { name: "Acknowledge & Continue" }).click();
  await expect(page.getByText("mex-dengue-2026")).toBeVisible();

  // Create a new Draft Bundle
  await page.getByRole("link", { name: "Analysis" }).click();
  await page.getByRole("button", { name: "New Draft Bundle" }).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await expect(page.getByText("Draft — Editable")).toBeVisible();

  // Rename the draft
  await page.locator('input[type="text"]').first().fill(analysisName);

  // Upload analysis code
  const zipBuffer = createZip([
    { name: "run.py", content: ANALYSIS_CODE },
    { name: "config.yaml", content: CONFIG_CONTENT },
    { name: "requirements.txt", content: "pandas\n" },
  ]);
  await page.getByRole("button", { name: "Upload ZIP" }).click();
  await page.getByText("Upload ZIP").click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "analysis-bundle.zip",
    mimeType: "application/zip",
    buffer: zipBuffer,
  });

  // Configure execution settings
  await page.getByLabel("Environment").selectOption({ label: "Python 3.13" });
  await page.locator("#edit-version-exec").fill("1.0.0");
  await page.waitForTimeout(1000);
  const entrypointSelect = page.locator("select").filter({ has: page.locator('option[value="run.py"]') }).first();
  if (await entrypointSelect.isVisible()) {
    await entrypointSelect.selectOption("run.py");
  }
  await page.getByLabel("Interpreter").selectOption("Python");
  await page.getByText("(mex-dengue-2026)").click();

  // Save and re-open
  await page.getByRole("button", { name: "Save and Close" }).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis$/);
  await page.getByText(analysisName).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);

  // Submit the bundle
  await page.getByRole("button", { name: "Submit for Review" }).click();
  await expect(page.getByText("Submitted")).toBeVisible();

  // ---------------------------------------------------------------
  // Submission Inspection tests begin here
  // ---------------------------------------------------------------

  // Navigate to Admin → Submissions
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("link", { name: "Submissions" }).click();
  await expect(page.getByText("Submission Operations")).toBeVisible();

  // Find the submitted bundle row
  const bundleRow = page.locator("tr").filter({ hasText: analysisName }).first();
  await expect(bundleRow).toBeVisible({ timeout: 15_000 });

  // Verify status badge shows Submitted
  await expect(bundleRow.getByText("Submitted")).toBeVisible();

  // Verify the Approve and Reject action buttons are visible
  await expect(bundleRow.getByRole("button", { name: "Approve" })).toBeVisible();
  await expect(bundleRow.getByRole("button", { name: "Reject" })).toBeVisible();

  // Click Inspect to expand the inspection panel
  await bundleRow.getByRole("button", { name: "Inspect" }).click();

  // Verify Overview section is visible
  await expect(page.getByText("Overview")).toBeVisible();
  await expect(page.getByText("Entrypoint")).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Submission Overview" }).getByText("run.py"),
  ).toBeVisible();
  await expect(page.getByText("Interpreter")).toBeVisible();
  await expect(page.getByText("python", { exact: true })).toBeVisible();
  await expect(page.locator("main").getByText("Resources", { exact: true })).toBeVisible();
  await expect(page.getByText("mex-dengue-2026")).toBeVisible();
  await expect(page.locator("main").getByText("Environment", { exact: true })).toBeVisible();
  await expect(page.getByText("Python 3.13")).toBeVisible();
  await expect(page.getByText("Build strategy")).toBeVisible();

  // Verify Bundle Files section is visible
  await expect(page.getByText("Bundle Files")).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Bundle Files" }).getByText("run.py"),
  ).toBeVisible();
  await expect(page.getByText("config.yaml")).toBeVisible();
  await expect(page.getByText("requirements.txt")).toBeVisible();

  // View a file and verify its content
  await page.locator("tr").filter({ hasText: "run.py" }).getByRole("button", { name: "View" }).click();
  await expect(page.getByText("import pandas as pd")).toBeVisible();

  // Close the file view
  await page.getByRole("button", { name: "Close" }).click();

  // Verify Governance History section is visible
  const govHistory = page.getByRole("region", {
    name: `Governance History - ${analysisName}`,
  });
  await expect(govHistory).toBeVisible();
  await expect(govHistory.getByText("Created")).toBeVisible();
  await expect(govHistory.getByText("Submitted")).toBeVisible();

  // Collapse the inspection panel
  await bundleRow.getByRole("button", { name: "Hide" }).click();
  await expect(page.getByText("Overview")).not.toBeVisible();
});
