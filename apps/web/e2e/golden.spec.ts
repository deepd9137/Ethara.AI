import { expect, test } from "@playwright/test";

/**
 * Golden-path E2E: signup → create project → arrive at project detail.
 *
 * This is intentionally the only E2E in the suite. It catches catastrophic
 * regressions across the full stack (DB migrations, auth flow, refresh cookie,
 * RBAC seeding, primary CRUD path). It does NOT replace unit/integration tests.
 *
 * Runs against http://localhost:5173 (Vite dev server) which proxies /v1 to
 * the FastAPI backend on :8000. Both must be up — the CI workflow boots them.
 */

const PASSWORD = "Password123";

function uniqueEmail() {
  return `e2e+${Date.now()}+${Math.random().toString(36).slice(2, 8)}@ttm.example`;
}

test("signup → create project → land on project detail", async ({ page }) => {
  const email = uniqueEmail();
  const projectName = `E2E Project ${Date.now()}`;

  // --- signup ---
  await page.goto("/signup");
  await expect(page.getByRole("heading", { name: /create your account|sign up/i })).toBeVisible({
    timeout: 10_000,
  });

  await page.getByLabel("Name").fill("E2E User");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();

  // Lands on dashboard
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 10_000 });

  // --- create project ---
  await page.goto("/projects");
  await page.getByRole("button", { name: /^(New project|Create a project)$/ }).click();

  // Dialog opens — fill name + submit
  await page.getByLabel("Name").fill(projectName);
  await page.getByRole("button", { name: "Create" }).click();

  // Dialog closes; project appears in the list
  await expect(page.getByText(projectName)).toBeVisible({ timeout: 10_000 });

  // --- open the project detail page ---
  await page.getByText(projectName).first().click();
  await expect(page.getByRole("heading", { name: projectName })).toBeVisible({
    timeout: 10_000,
  });
});
