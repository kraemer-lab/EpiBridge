import { test, expect } from "@playwright/test";
import { login } from "../helpers/auth";
import {
  RESEARCHER_EMAIL,
  ensureTermsPublished,
  createUser,
  provisionProject,
  createAndSubmitBundle,
} from "../helpers/setup";

test("Moderator Acceptance", async ({ page }) => {
  const TS = Date.now();
  const moderatorEmail = `moderator-${TS}@setup.local`;
  const analysisName = `Review Analysis ${TS}`;

  // Setup: terms, users (moderator), project (with researcher + moderator), submitted bundle
  await ensureTermsPublished();
  await createUser(moderatorEmail, "Moderator Persona", ["moderator"]);
  const project = await provisionProject(TS, RESEARCHER_EMAIL, moderatorEmail);
  await createAndSubmitBundle(project.id, analysisName);

  // Login as moderator
  await login(page, moderatorEmail, "testpass123");
  await expect(page.getByTestId("header-user-name")).toBeVisible();

  // Navigate to Admin → Submissions
  await page.getByRole("link", { name: "Admin" }).click();
  await page
    .getByRole("navigation", { name: "Admin tabs" })
    .getByRole("link", { name: "Submissions" })
    .click();
  await expect(page.getByText("Submission Operations")).toBeVisible();

  // Find the submitted bundle
  const bundleRow = page.locator("tr").filter({ hasText: analysisName }).first();
  await expect(bundleRow).toBeVisible({ timeout: 15_000 });

  // Verify the bundle is in Submitted status
  await expect(bundleRow.getByText("Submitted")).toBeVisible();
  await expect(bundleRow.getByRole("button", { name: "Approve" })).toBeVisible();
  await expect(bundleRow.getByRole("button", { name: "Reject" })).toBeVisible();

  // Inspect the bundle
  await bundleRow.getByRole("button", { name: "Inspect" }).click();
  await expect(page.getByText("Overview")).toBeVisible();
  await expect(page.getByText("Bundle Files")).toBeVisible();

  // Approve the bundle — the row disappears from "Awaiting Review" after
  // approval since the status changes to approved_for_execution
  await bundleRow.getByRole("button", { name: "Approve" }).click();

  // Switch to "Approved" filter to verify the status change
  await page.getByRole("button", { name: "Approved", exact: true }).click();
  await expect(
    page.locator("tr").filter({ hasText: analysisName }).first().getByText("Approved for Execution"),
  ).toBeVisible({ timeout: 10_000 });

  await page.getByRole("button", { name: "Sign out" }).click();
});
