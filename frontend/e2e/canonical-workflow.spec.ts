import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import fs from "fs";
import { createZip } from "./helpers/zip";

const TS = Date.now();

const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "admin@epibridge.local";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin";

const ANALYSIS_CODE = `\
import pandas as pd
df = pd.read_csv("/data/mexico_dengue_2026/demo.csv")
summary = df.describe()
summary.to_csv("/output/summary.csv")
print(f"Analysis complete. Processed {len(df)} rows, {len(df.columns)} columns.")
`;

test("Canonical Workflow: researcher creates project, uploads bundle, runs analysis, approves output set, downloads release package", async ({
  page,
}) => {
  const projectName = `Canonical Workflow Test ${TS}`;
  const analysisName = `Test Analysis ${TS}`;

  // 1. Open EpiBridge — redirected to login
  await page.goto("/login");

  // 2. Sign in with admin credentials
  await page.fill("#email", ADMIN_EMAIL);
  await page.fill("#password", ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("/", { timeout: 15000 });

  // 3. Verify admin is shown in header
  await expect(page.getByTestId("header-user-name")).toHaveText("Administrator");

  // 4. Navigate to Environments page and verify environment discovery
  await page.getByRole("link", { name: "Environments" }).click();
  await expect(page.getByRole("heading", { name: "Execution Environments" })).toBeVisible();
  await expect(page.locator("table")).toBeVisible();
  await expect(page.getByText("Python 3.13").first()).toBeVisible();
  await page.getByText("Python 3.13").first().click();

  // 5. Verify environment detail page
  await expect(page.getByRole("heading", { name: "Environment Details" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Local Development" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dockerfile" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Published Artefacts" })).toBeVisible();
  await expect(page.getByText("Pull the image")).toBeVisible();
  await expect(page.getByText("Run a container")).toBeVisible();

  // 6. Navigate back and then to Projects page
  await page.getByRole("link", { name: "← Environments" }).click();
  await page.getByRole("link", { name: "Projects" }).click();

  // 7. Create a new project
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.getByPlaceholder("Project name").fill(projectName);
  await page.getByPlaceholder("Optional description").fill("End-to-end test project");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();

  // 8. Open the project
  await page.getByText(projectName).click();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  // 9. Open the Resources tab and attach the Mexico dengue data resource
  await page.getByRole("link", { name: "Resources" }).click();
  await expect(page.getByText("Configure Resources")).toBeVisible();
  await page.locator("tr").filter({ hasText: "mex-dengue-2026" }).getByRole("button", { name: "Attach" }).click();
  await expect(page.getByText("mex-dengue-2026")).toBeVisible();

  // 10. Open the Analysis tab
  await page.getByRole("link", { name: "Analysis" }).click();
  await expect(page.getByTestId("analysis-heading")).toBeVisible();

  // 11. Navigate to Create Analysis
  await page.getByRole("link", { name: "Create Analysis" }).click();

  // 12. Fill the form
  await page.getByLabel("Name").fill(analysisName);
  await page.getByLabel("Version").fill("1.0.0");
  await page.getByLabel("Entrypoint").fill("run.py");
  await page.getByLabel("Interpreter").selectOption("Python");
  await page.getByLabel("Execution Environment").selectOption({ label: "Python 3.13" });
  await page.getByText("mex-dengue-2026").click();

  // 13. Upload the analysis bundle ZIP
  const zipBuffer = createZip([
    { name: "run.py", content: ANALYSIS_CODE },
    { name: "requirements.txt", content: "" },
  ]);
  await page
    .locator('input[type="file"]')
    .setInputFiles({ name: "analysis-bundle.zip", mimeType: "application/zip", buffer: zipBuffer });

  // 14. Save
  await page.getByRole("button", { name: "Save" }).click();

  // 15. Wait for redirect to analysis list, then open the bundle
  await page.waitForURL(/\/projects\/[^/]+\/analysis$/);
  await expect(page.getByTestId("analysis-heading")).toBeVisible();
  await expect(page.getByText(analysisName)).toBeVisible();
  await page.getByText(analysisName).click();

  // 16. Submit the bundle (DRAFT → SUBMITTED) via the Submit button
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Submitted")).toBeVisible();

  // 17. Approve the bundle (SUBMITTED → APPROVED_FOR_EXECUTION) via the Approve button
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("Approved for Execution")).toBeVisible();

  // 18. Run Analysis button is now visible; click it
  await page.getByRole("button", { name: "Run Analysis" }).click();

  // 19. Wait for the Execution Request to transition: PENDING → RUNNING → COMPLETED
  await expect(
    page.locator("tr").filter({ hasText: analysisName }).getByText("completed")
  ).toBeVisible({ timeout: 180_000 });

  // 20. Navigate to Admin → Outputs to review and release the output set
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("link", { name: "Outputs" }).click();

  // 21. Find the output set row for this test's analysis and click Approve
  const setRow = page.locator("tr").filter({ hasText: analysisName }).first();
  await expect(setRow).toBeVisible({ timeout: 30_000 });
  await setRow.getByRole("button", { name: "Approve" }).click();
  await expect(setRow.getByText("Approved")).toBeVisible();

  // 22. Click Release
  await setRow.getByRole("button", { name: "Release" }).click();
  await expect(setRow.getByText("Released")).toBeVisible();

  // 23. Navigate back to the project outputs page
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByText(projectName).click();
  await page.getByRole("link", { name: "Outputs" }).click();

  // 24. Download the Release Package ZIP
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download All" }).click(),
  ]);

  // 25. Navigate to Admin Audit Log and verify governance events are recorded
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("link", { name: "Audit Log" }).click();
  await expect(page.getByText("Audit Log")).toBeVisible();
  const auditTable = page.locator(".table");
  await expect(auditTable.getByText("project.created").first()).toBeVisible({ timeout: 10_000 });
  await expect(auditTable.getByText("bundle.submitted").first()).toBeVisible();
  await expect(auditTable.getByText("bundle.approved").first()).toBeVisible();
  await expect(auditTable.getByText("execution.requested").first()).toBeVisible();
  await expect(auditTable.getByText("execution.completed").first()).toBeVisible();
  await expect(auditTable.getByText("output_set.approved").first()).toBeVisible();
  await expect(auditTable.getByText("output_set.released").first()).toBeVisible();

  // 26. Verify the downloaded file is a ZIP containing summary.csv
  expect(download.suggestedFilename()).toMatch(/\.zip$/);
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  if (downloadPath) {
    const stats = fs.statSync(downloadPath);
    expect(stats.size).toBeGreaterThan(0);

    const listing = execSync(`unzip -l "${downloadPath}"`, { encoding: "utf-8" });
    expect(listing).toContain("summary.csv");
    expect(listing).toContain("execution_metadata.json");
  }
});
