import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import * as fs from "fs";
import { createZip } from "./helpers/zip";

const TS = Date.now();

const MAINTAINER_EMAIL = process.env.MAINTAINER_EMAIL || "maintainer@epibridge.local";
const MAINTAINER_PASSWORD = process.env.MAINTAINER_PASSWORD || "maintainer";

/*
 * This analysis proves the custom Dockerfile was genuinely used during image construction.
 *
 * Provenance chain:
 *   Custom Build Strategy
 *   → Custom Dockerfile (build/Dockerfile in the bundle)
 *   → The Dockerfile creates /opt/epibridge-proof/build_proof.txt during docker build
 *   → This file is baked into the ExecutionImage
 *   → When the execution container starts from that image, the file is present on disk
 *   → The analysis reads it and writes its content to the output
 *   → The output is captured in the release package
 *   → We download the release package and verify the content
 *
 * If the output contains PROOF:CUSTOM_BUILD_MARKER, the custom Dockerfile was used.
 * The institutional template never creates this file.
 */
const ANALYSIS_CODE = `\
import os
proof_path = "/opt/epibridge-proof/build_proof.txt"
result = "NOT_FOUND"
if os.path.exists(proof_path):
    with open(proof_path) as f:
        result = f.read().strip()
with open("/output/build_proof.txt", "w") as f:
    f.write(f"PROOF:{result}")
`;

const CUSTOM_DOCKERFILE = `\
ARG BASE_IMAGE
FROM ${"${BASE_IMAGE}"}
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \\
    mkdir -p /opt/epibridge-proof && \\
    echo "CUSTOM_BUILD_MARKER" > /opt/epibridge-proof/build_proof.txt && \\
    chmod -R 755 /opt/epibridge-proof && \\
    rm -f /tmp/requirements.txt
`;

test("Custom Build Workflow: researcher creates project with Custom Build strategy, custom Dockerfile is used to build execution image, output proves customisation", async ({
  page,
}) => {
  const projectName = `Custom Build Test ${TS}`;
  const analysisName = `Custom Build Analysis ${TS}`;

  // 1. Login as maintainer (has build.customize capability via role seeding)
  await page.goto("/login");
  await page.fill("#email", MAINTAINER_EMAIL);
  await page.fill("#password", MAINTAINER_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("/", { timeout: 15000 });
  await expect(page.getByTestId("header-user-name")).toHaveText("Maintainer");

  // 2. Create project
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.getByPlaceholder("Project name").fill(projectName);
  await page.getByPlaceholder("Optional description").fill("Custom Build e2e test");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();

  // 3. Open the project
  await page.getByText(projectName).click();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  // 4. Attach data resource
  await page.getByRole("link", { name: "Resources" }).click();
  await page
    .locator("tr")
    .filter({ hasText: "mex-dengue-2026" })
    .getByRole("button", { name: "Attach" })
    .click();
  await expect(page.getByText("mex-dengue-2026")).toBeVisible();

  // 5. Navigate to Create Analysis
  await page.getByRole("link", { name: "Analysis" }).click();
  await page.getByRole("link", { name: "Create Analysis" }).click();

  // 6. Fill the form
  await page.getByLabel("Name").fill(analysisName);
  await page.getByLabel("Version").fill("2.0.0");
  await page.getByLabel("Entrypoint").fill("run.py");
  await page.getByLabel("Interpreter").selectOption("Python");
  await page.getByLabel("Execution Environment").selectOption({ label: "Python 3.13" });
  await page.getByText("mex-dengue-2026").click();

  // 7. Select Custom Build strategy
  await page.getByLabel("Build Strategy").selectOption("Custom Build");

  // 8. Upload the analysis bundle ZIP containing the custom Dockerfile
  const zipBuffer = createZip([
    { name: "run.py", content: ANALYSIS_CODE },
    { name: "requirements.txt", content: "" },
    { name: "build/Dockerfile", content: CUSTOM_DOCKERFILE },
  ]);
  await page
    .locator('input[type="file"]')
    .setInputFiles({
      name: "custom-build-bundle.zip",
      mimeType: "application/zip",
      buffer: zipBuffer,
    });

  // 9. Save
  await page.getByRole("button", { name: "Save" }).click();

  // 10. Wait for redirect and open the bundle
  await page.waitForURL(/\/projects\/[^/]+\/analysis$/);
  await expect(page.getByTestId("analysis-heading")).toBeVisible();
  await expect(page.getByText(analysisName)).toBeVisible();
  await page.getByText(analysisName).click();

  // 11. Verify Build Strategy shows Custom Build
  await expect(page.getByText("Custom Build", { exact: true })).toBeVisible();

  // 12. Submit the bundle (DRAFT → SUBMITTED)
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Submitted")).toBeVisible();

  // 13. Approve the bundle (SUBMITTED → APPROVED_FOR_EXECUTION)
  //     This triggers ensure_build_request(), which creates a BuildRequest
  //     because the custom Dockerfile produces a new dependency hash.
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("Approved for Execution")).toBeVisible();

  // 14. Wait for the execution image build to complete.
  //     The worker:
  //       1. Receives the BuildRequest from the database
  //       2. Detects bundle.build_strategy == "custom"
  //       3. Uses bundle_path/build/Dockerfile instead of the curated template
  //       4. Runs docker build, which creates /opt/epibridge-proof/build_proof.txt in the image
  //       5. Creates an ExecutionImage record and links it to the bundle
  //       6. Sets bundle.build_status = ENVIRONMENT_READY
  //     The frontend polls every 5s and shows "Ready to run" when complete.
  await expect(page.getByText("Ready to run")).toBeVisible({ timeout: 120_000 });

  // 15. Run Analysis — creates ExecutionRequest
  await page.getByRole("button", { name: "Run Analysis" }).click();

  // 16. Wait for execution to complete
  await expect(
    page.locator("tr").filter({ hasText: analysisName }).getByText("completed")
  ).toBeVisible({ timeout: 180_000 });

  // 17. Navigate to Admin → Outputs to approve and release
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("link", { name: "Outputs" }).click();

  const setRow = page.locator("tr").filter({ hasText: analysisName }).first();
  await expect(setRow).toBeVisible({ timeout: 30_000 });
  await setRow.getByRole("button", { name: "Approve" }).click();
  await expect(setRow.getByText("Approved")).toBeVisible();

  await setRow.getByRole("button", { name: "Release" }).click();
  await expect(setRow.getByText("Released")).toBeVisible();

  // 18. Navigate to project outputs and download release package
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByText(projectName).click();
  await page.getByRole("link", { name: "Outputs" }).click();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download All" }).click(),
  ]);

  // 19. Verify the downloaded release package contains build_proof.txt
  //     with PROOF:CUSTOM_BUILD_MARKER.
  //     This proves the entire chain:
  //       Custom Build Strategy → Custom Dockerfile → ExecutionImage → Execution → Output
  expect(download.suggestedFilename()).toMatch(/\.zip$/);
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  if (downloadPath) {
    const stats = fs.statSync(downloadPath);
    expect(stats.size).toBeGreaterThan(0);

    const extractDir = `/tmp/epibridge-custom-build-proof-${TS}`;
    execSync(`unzip -o "${downloadPath}" -d "${extractDir}"`, { encoding: "utf-8" });
    try {
      const proofContent = fs
        .readFileSync(`${extractDir}/build_proof.txt`, "utf-8")
        .trim();
      expect(proofContent).toBe("PROOF:CUSTOM_BUILD_MARKER");
    } finally {
      execSync(`rm -rf "${extractDir}"`);
    }
  }
});
