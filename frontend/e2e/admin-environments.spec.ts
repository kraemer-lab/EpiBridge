import { test, expect } from "@playwright/test";
import { login } from "./helpers/auth";

const BASE = process.env.PLAYWRIGHT_BASE_URL || "https://localhost";

const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "admin@epibridge.local";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin";

test("Admin Environments — Publication Discovery", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  // Publish platform terms via API (admin routes require terms acceptance)
  await page.request.post(`${BASE}/api/admin/terms/platform`, {
    data: {
      version: "1.0.0",
      title: "EpiBridge Platform Terms of Service",
      content: "## Terms\n\nBy using this platform you agree to these terms.",
    },
  });

  // Navigate to Admin → Environments
  await page.getByRole("link", { name: "Admin" }).click();
  await page
    .getByRole("navigation", { name: "Admin tabs" })
    .getByRole("link", { name: "Environments" })
    .click();
  await expect(page.getByRole("heading", { name: "Execution Environments" })).toBeVisible();

  // Verify known execution environments are listed
  await expect(page.getByRole("cell", { name: "Python 3.13" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Python 3.14" })).toBeVisible();

  // Verify runtime information is displayed
  await expect(page.getByRole("cell", { name: "python-3.13", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "python-3.14", exact: true })).toBeVisible();

  // Verify status badges show "active" for the seeded environments
  const activeBadges = page.locator("span").filter({ hasText: "active" });
  await expect(activeBadges.first()).toBeVisible();
  await expect(await activeBadges.count()).toBeGreaterThanOrEqual(3);
});
