// Conda Execution Environment Acceptance
//
// Verifies the published conda execution environment honours its execution
// contract:
//   - validation installs declared conda dependencies
//   - build produces a runnable execution image
//   - governed execution succeeds with a non-Python entrypoint
//   - expected outputs are produced
//
// This is NOT a persona test. Institutional workflows (project provisioning,
// bundle creation, submission, approval, output release) are handled by
// helpers and are not under test here.
//
// Unlike the Python acceptance test, this test uses a shell entrypoint
// (run.sh) to prove that the conda environment supports non-Python
// executables installed via the conda package manager.

import { test, expect } from "@playwright/test";
import { createZip } from "../helpers/zip";
import { login } from "../helpers/auth";
import { RESEARCHER_EMAIL } from "../helpers/setup";
import {
  provisionExecutionTestProject,
  createExecutionBundle,
  approveBundle,
  pollBuild,
  approveAndReleaseOutputSetForBundle,
  verifyArchiveContents,
} from "../helpers/ee-helpers";

test("Conda execution environment acceptance", async ({ page }) => {
  test.setTimeout(600_000);
  const TS = Date.now();
  const bundleName = `Conda EE ${TS}`;

  // === SETUP (API) ===
  const project = await provisionExecutionTestProject(TS);
  const { bundleId } = await createExecutionBundle(
    project.id,
    bundleName,
    "conda",
    "run.sh",
    "shell",
  );

  // === VALIDATION (UI: upload, trigger, wait) ===
  await login(page, RESEARCHER_EMAIL, "researcher");
  await page.getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByText(project.name).click();
  await page.getByRole("link", { name: "Analysis" }).click();
  await page.getByText(bundleName).click();
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);

  const zipBuffer = createZip([
    { name: "run.sh", content: `\
jq --version > /output/jq_version.txt 2>&1
echo "jq is available"
`},
    {
      name: "environment.yml",
      content: `\
name: analysis
channels:
  - conda-forge
dependencies:
  - jq
`,
    },
  ]);
  await page.getByRole("button", { name: "Upload ZIP" }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "bundle.zip",
    mimeType: "application/zip",
    buffer: zipBuffer,
  });

  await page.getByRole("button", { name: "Run Validation" }).click();
  await expect(
    page
      .locator(".card")
      .filter({ hasText: "Validation Run" })
      .getByText(/completed/),
  ).toBeVisible({ timeout: 180_000 });

  // === SUBMIT (via browser session) & APPROVE (API) ===
  const submitResp = await page.request.post(
    `/api/projects/${project.id}/bundles/${bundleId}/submit`,
  );
  expect(submitResp.ok()).toBeTruthy();
  await approveBundle(bundleId, project.moderatorEmail);

  // === BUILD (API via browser session: no session conflict) ===
  await pollBuild(project.id, bundleId, page.request);

  // === EXECUTION (UI: trigger, wait) ===
  await page.goto(`/projects/${project.id}/analysis/${bundleId}`);
  await page.waitForURL(/\/projects\/[^/]+\/analysis\/[^/]+$/);
  await page.getByRole("button", { name: "Run Analysis" }).click();
  await expect(
    page.locator("tr").filter({ hasText: bundleName }).getByText("completed"),
  ).toBeVisible({ timeout: 180_000 });

  // === OUTPUT RELEASE (API: admin context, no session conflict) ===
  await approveAndReleaseOutputSetForBundle(bundleId, project.id);

  // === DOWNLOAD (UI) ===
  await page.goto(`/projects/${project.id}`);
  await page.getByRole("link", { name: "Outputs" }).click();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download All" }).click(),
  ]);
  await verifyArchiveContents(download, ["jq_version.txt"]);
});
