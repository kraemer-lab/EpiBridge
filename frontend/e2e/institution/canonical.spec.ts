import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import * as fs from "fs";
import { createZip } from "../helpers/zip";
import { login } from "../helpers/auth";

const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "admin@epibridge.local";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin";
const MAINTAINER_EMAIL =
  process.env.MAINTAINER_EMAIL || "maintainer@epibridge.local";
const MAINTAINER_PASSWORD = process.env.MAINTAINER_PASSWORD || "maintainer";

const ANALYSIS_CODE = `\
import pandas as pd
df = pd.read_csv("/data/demo-surveillance/demo.csv")
summary = df.describe()
summary.to_csv("/output/summary.csv")
print(f"Complete. Processed {len(df)} rows.")
`;

test("Canonical Workflow", async ({ page }) => {
  test.setTimeout(600_000);
  const TS = Date.now();
  const researcherEmail = `researcher-can-${TS}@test.local`;
  const moderatorEmail = `moderator-can-${TS}@test.local`;
  const projectName = `Canonical ${TS}`;
  const analysisName = `Analysis ${TS}`;

  // ===================================================================
  // 1. ADMINISTRATOR — publish terms, create users
  // ===================================================================
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await expect(page.getByTestId("header-user-name")).toHaveText("Administrator");

  await page.request.post("/api/admin/terms/platform", {
    data: { version: TS.toString(), title: "EpiBridge Platform Terms", content: "## Terms\n\nBy using this platform you agree." },
  });
  await page.request.post("/api/admin/users", {
    data: { email: researcherEmail, display_name: "Canonical Researcher", password: "testpass123", roles: ["researcher"] },
  });
  await page.request.post("/api/admin/users", {
    data: { email: moderatorEmail, display_name: "Canonical Moderator", password: "testpass123", roles: ["moderator"] },
  });
  await page.getByRole("button", { name: "Sign out" }).click();

  // ===================================================================
  // 2. MAINTAINER — create project, add members, attach resource
  // ===================================================================
  await login(page, MAINTAINER_EMAIL, MAINTAINER_PASSWORD);
  await expect(page.getByTestId("header-user-name")).toHaveText("Maintainer");

  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.getByPlaceholder("Project name").fill(projectName);
  await page.getByPlaceholder("Optional description").fill("Canonical workflow project");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  await page.getByText(projectName).click();
  await page.waitForURL(/\/projects\//);

  const projectId = page.url().match(/\/projects\/([^/]+)/)?.[1];
  if (!projectId) throw new Error("Could not extract project ID");

  // Add members via the search UI
  await page.getByRole("link", { name: "Members" }).click();
  await page.getByPlaceholder("Search by name or email...").fill(researcherEmail);
  await page.locator("div").filter({ hasText: researcherEmail }).first().click();
  await page.getByRole("button", { name: "Add Member" }).click();
  await expect(page.getByText(researcherEmail)).toBeVisible();

  await page.getByPlaceholder("Search by name or email...").fill(moderatorEmail);
  await page.locator("div").filter({ hasText: moderatorEmail }).first().click();
  await page.getByRole("button", { name: "Add Member" }).click();
  await expect(page.getByText(moderatorEmail)).toBeVisible();

  await page.getByRole("link", { name: "Resources", exact: true }).click();
  await expect(page.getByText("Configure Resources")).toBeVisible();
  await page.locator("tr").filter({ hasText: "demo-surveillance" }).getByRole("button", { name: "Attach" }).click();
  await page.getByRole("button", { name: "Accept & Continue" }).click();
  await expect(page.getByText("demo-surveillance")).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();

  // Accept platform + resource terms for the researcher
  await page.request.post("/api/auth/login", { data: { email: researcherEmail, password: "testpass123" } });
  await page.request.post("/api/terms/platform/accept").catch(() => {});
  const resReq = await page.request.get("/api/resources");
  if (resReq.ok()) {
    const resources = await resReq.json();
    const resource = resources.find((r: any) => r.identifier === "demo-surveillance");
    if (resource) await page.request.post(`/api/terms/resources/${resource.id}/accept`).catch(() => {});
  }

  // ===================================================================
  // 3. RESEARCHER — create bundle, validate, submit
  // ===================================================================
  await login(page, researcherEmail, "testpass123");
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByText(projectName).click();
  await page.getByRole("link", { name: "Analysis" }).click();
  await page.getByRole("button", { name: "New Draft Bundle" }).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await page.locator('input[type="text"]').first().fill(analysisName);

  const zipBuffer = createZip([
    { name: "run.py", content: ANALYSIS_CODE },
    { name: "requirements.txt", content: "" },
  ]);
  await page.getByRole("button", { name: "Upload ZIP" }).click();
  await page.locator('input[type="file"]').setInputFiles({ name: "bundle.zip", mimeType: "application/zip", buffer: zipBuffer });
  await page.getByLabel("Environment").selectOption({ label: "Python 3.13" });
  await page.locator("#edit-version-exec").fill("1.0.0");
  await page.waitForTimeout(1000);
  const entrypointSelect = page.locator("select").filter({ has: page.locator('option[value="run.py"]') }).first();
  if (await entrypointSelect.isVisible()) await entrypointSelect.selectOption("run.py");
  await page.getByLabel("Interpreter").selectOption("Python");
  await page.getByText("(demo-surveillance)").click();

  await page.getByRole("button", { name: "Run Validation" }).click();
  await expect(page.locator(".card").filter({ hasText: "Validation Run" }).getByText(/completed/)).toBeVisible({ timeout: 180_000 });

  await page.getByRole("button", { name: "Save and Close" }).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis$/);
  await page.getByText(analysisName).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await page.getByRole("button", { name: "Submit for Review" }).click();
  await expect(page.getByText("Submitted")).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();

  // ===================================================================
  // 4. MODERATOR — review and approve bundle
  // ===================================================================
  await login(page, moderatorEmail, "testpass123");
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("navigation", { name: "Admin tabs" }).getByRole("link", { name: "Submissions" }).click();
  await expect(page.getByText("Submission Operations")).toBeVisible();

  const bundleRow = page.locator("tr").filter({ hasText: analysisName }).first();
  await expect(bundleRow).toBeVisible({ timeout: 15_000 });
  await bundleRow.getByRole("button", { name: "Approve" }).click();

  await page.getByRole("button", { name: "Approved", exact: true }).click();
  await expect(page.locator("tr").filter({ hasText: analysisName }).first().getByText("Approved for Execution")).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Sign out" }).click();

  // ===================================================================
  // 5. RESEARCHER — run approved analysis
  // ===================================================================
  await login(page, researcherEmail, "testpass123");
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByText(projectName).click();
  await page.getByRole("link", { name: "Analysis" }).click();
  await page.getByText(analysisName).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await page.getByRole("button", { name: "Run Analysis" }).click();
  await expect(page.locator("tr").filter({ hasText: analysisName }).getByText("completed")).toBeVisible({ timeout: 180_000 });
  await page.getByRole("button", { name: "Sign out" }).click();

  // ===================================================================
  // 6. MODERATOR — approve output, verify audit
  // ===================================================================
  await login(page, moderatorEmail, "testpass123");
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("navigation", { name: "Admin tabs" }).getByRole("link", { name: "Outputs" }).click();

  const setRow = page.locator("tr").filter({ hasText: analysisName }).first();
  await expect(setRow).toBeVisible({ timeout: 30_000 });
  await setRow.getByRole("button", { name: "Approve" }).click();
  await expect(setRow.getByText("Approved")).toBeVisible();

  // Verify audit events while still moderator
  await page.getByRole("navigation", { name: "Admin tabs" }).getByRole("link", { name: "Audit Log" }).click();
  await expect(page.getByText("Audit Log")).toBeVisible();
  await expect(page.getByText("project.created").first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("bundle.submitted").first()).toBeVisible();
  await expect(page.getByText("bundle.approved").first()).toBeVisible();
  await expect(page.getByText("execution.requested").first()).toBeVisible();
  await expect(page.getByText("execution.completed").first()).toBeVisible();
  await expect(page.getByText("output_set.approved").first()).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();

  // ===================================================================
  // 6b. MAINTAINER — release output set via API
  // ===================================================================
  await page.request.post("/api/auth/login", { data: { email: moderatorEmail, password: "testpass123" } });
  await page.request.post("/api/terms/platform/accept");
  const modSetsResp = await page.request.get("/api/admin/output-sets");
  const modSets = modSetsResp.ok() ? await modSetsResp.json() : [];
  const targetSet = modSets.find(
    (s: any) => s.execution_request_name?.includes(analysisName) && s.status === "approved",
  );
  if (!targetSet) throw new Error("Output set not found for release");
  await page.request.post("/api/auth/login", { data: { email: MAINTAINER_EMAIL, password: MAINTAINER_PASSWORD } });
  await page.request.post("/api/terms/platform/accept");
  const releaseResp = await page.request.post(`/api/admin/output-sets/${targetSet.id}/release`);
  if (!releaseResp.ok()) throw new Error(`Release failed: ${await releaseResp.text()}`);

  // ===================================================================
  // 7. RESEARCHER — download released outputs
  // ===================================================================
  await login(page, researcherEmail, "testpass123");
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByText(projectName).click();
  await page.getByRole("link", { name: "Outputs" }).click();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download All" }).click(),
  ]);

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

  await page.getByRole("button", { name: "Sign out" }).click();
});
