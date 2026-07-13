import { test, expect } from "@playwright/test";
import { login } from "../helpers/auth";
import {
  MAINTAINER_EMAIL,
  RESEARCHER_EMAIL,
  RESOURCE_IDENTIFIER,
  ensureTermsPublished,
  createUser,
} from "../helpers/setup";

const MAINTAINER_PASSWORD = process.env.MAINTAINER_PASSWORD || "maintainer";

test("Maintainer Acceptance", async ({ page }) => {
  const TS = Date.now();
  const moderatorEmail = `moderator-${TS}@setup.local`;
  const projectName = `Maintainer Test ${TS}`;

  await ensureTermsPublished();
  await createUser(moderatorEmail, "Moderator Persona", ["moderator"]);

  await login(page, MAINTAINER_EMAIL, MAINTAINER_PASSWORD);
  await expect(page.getByTestId("header-user-name")).toHaveText("Maintainer");

  // Create a project via the UI
  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.getByPlaceholder("Project name").fill(projectName);
  await page.getByPlaceholder("Optional description").fill("Maintainer acceptance");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  await page.getByText(projectName).click();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  // Add researcher as a project member via the search UI
  await page.getByRole("link", { name: "Members" }).click();
  await expect(page.getByText("Members")).toBeVisible();
  await page.getByPlaceholder("Search by name or email...").fill(RESEARCHER_EMAIL);
  await page.locator("div").filter({ hasText: RESEARCHER_EMAIL }).first().click();
  await page.getByRole("button", { name: "Add Member" }).click();
  await expect(page.getByText(RESEARCHER_EMAIL)).toBeVisible();

  // Add moderator as a project member via the search UI
  await page.getByPlaceholder("Search by name or email...").fill(moderatorEmail);
  await page.locator("div").filter({ hasText: moderatorEmail }).first().click();
  await page.getByRole("button", { name: "Add Member" }).click();
  await expect(page.getByText(moderatorEmail)).toBeVisible();

  // Attach a data resource via the UI
  await page.getByRole("link", { name: "Resources", exact: true }).click();
  await expect(page.getByText("Configure Resources")).toBeVisible();
  await page
    .locator("tr")
    .filter({ hasText: RESOURCE_IDENTIFIER })
    .getByRole("button", { name: "Attach" })
    .click();
  await page.getByRole("button", { name: "Accept & Continue" }).click();
  await expect(page.getByText(RESOURCE_IDENTIFIER)).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
});
