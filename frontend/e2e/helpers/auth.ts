import { expect, type Page } from "@playwright/test";

export async function login(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  // Authenticate directly via the API, bypassing the frontend login form.
  // This avoids a race condition where the client-side router.replace("/")
  // triggers a server-side Next.js render before the session cookie set by
  // the login response has propagated, causing the middleware to redirect
  // back to /login.  Playwright's page.request.post() stores the Set-Cookie
  // response header in the browser context, so subsequent navigations
  // carry the session cookie correctly.
  const loginRes = await page.request.post("/api/auth/login", {
    data: { email, password },
  });
  if (!loginRes.ok()) {
    throw new Error(
      `Login API failed (${loginRes.status()}): ${await loginRes.text()}`,
    );
  }

  // Navigate to the application root.  The session cookie from the login
  // response is carried with this request, so the Next.js middleware
  // allows the page through and the AuthProvider loads the authenticated
  // user.
  await page.goto("/");

  // The [data-testid="header-user-name"] element renders only after:
  //   - AuthProvider resolved user state;
  //   - AuthGate completed its routing decision;
  //   - any mandatory terms flow has been satisfied;
  //   - the full application shell (Header, Sidebar) has rendered.
  //
  // If terms acceptance is required, the AuthGate routes to /terms.
  // Handle that by checking for the terms page and accepting.
  const appReady = page.getByTestId("header-user-name");
  try {
    await appReady.waitFor({ state: "visible", timeout: 15000 });
  } catch {
    if (page.url().includes("/terms")) {
      await expect(
        page.getByRole("button", { name: "Accept" }),
      ).toBeVisible();
      await page.getByRole("button", { name: "Accept" }).click();
      await appReady.waitFor({ state: "visible", timeout: 15000 });
    } else {
      throw new Error(
        "Login did not complete within 15s — the test environment may be " +
        "under load. Check backend and database availability.",
      );
    }
  }
}
