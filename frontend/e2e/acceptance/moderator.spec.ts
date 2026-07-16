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

  // Navigate to Review → Analyses
  await page.getByRole("link", { name: "Review", exact: true }).click();
  await page
    .getByRole("navigation", { name: "Review tabs" })
    .getByRole("link", { name: "Analyses" })
    .click();
  await expect(page.getByText("Analysis Operations")).toBeVisible();

  // Find the submitted bundle
  const bundleRow = page.locator("tr").filter({ hasText: analysisName }).first();
  await expect(bundleRow).toBeVisible({ timeout: 15_000 });

  // Verify the bundle is in Submitted status
  await expect(bundleRow.getByText("Submitted")).toBeVisible();

  // Inspect the bundle to reveal governance actions
  await bundleRow.getByRole("button", { name: "Inspect" }).click();
  await expect(page.getByText("Overview")).toBeVisible();
  await expect(page.getByText("Bundle Files")).toBeVisible();

  // Approve the bundle — the row disappears from "Awaiting Review" after
  // approval since the status changes to approved_for_execution
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByRole("button", { name: "Approve Analysis", exact: true }).click();

  // Switch to "Approved" filter to verify the status change
  await page.getByRole("button", { name: "Approved", exact: true }).click();
  await expect(
    page.locator("tr").filter({ hasText: analysisName }).first().getByText("Approved for Execution"),
  ).toBeVisible({ timeout: 10_000 });

  await page.getByRole("button", { name: "Sign out" }).click();
});
