import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const session = {
  ready: true,
  max_duration_seconds: 1800,
  max_file_bytes: 262144000,
  retention_seconds: 3600,
  max_quality: 720,
  max_active: 1,
  tier: "guest",
  account: null,
  login_providers: [],
  quota: { limit: 3, remaining: 2, window_seconds: 3600, resets_at: null },
  plans: [
    {
      tier: "guest",
      downloads: 3,
      window_seconds: 3600,
      max_active: 1,
      max_quality: 720,
      max_duration_seconds: 1800,
      max_file_bytes: 262144000,
    },
    {
      tier: "free",
      downloads: 20,
      window_seconds: 86400,
      max_active: 2,
      max_quality: 1080,
      max_duration_seconds: 7200,
      max_file_bytes: 524288000,
    },
  ],
};
const ready = {
  id: "e".repeat(32),
  provider: "youtube",
  title: "A walk through the mountains",
  state: "complete",
  kind: "mp4",
  quality: 720,
  file_bytes: 15360000,
  expires_at: Date.now() / 1000 + 3000,
};
const failed = {
  id: "f".repeat(32),
  provider: "instagram",
  title: "Morning on the coast",
  state: "failed",
  kind: "mp3",
  quality: 192,
  error: "audio_unavailable",
  expires_at: Date.now() / 1000 + 3000,
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ytd-language", "en"));
  await page.route("**/api/session", (route) =>
    route.fulfill({ json: session }),
  );
  await page.route("**/api/jobs", (route) =>
    route.fulfill({ json: [ready, failed] }),
  );
});

test("keeps the same preview element and keyboard focus during polling", async ({
  page,
}) => {
  await page.route(`**/api/jobs/${ready.id}/preview`, (route) =>
    route.fulfill({ contentType: "video/mp4", body: "synthetic-media" }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Play", exact: true }).click();
  const media = page.locator("video");
  await expect(media).toHaveCount(1);
  await media.evaluate((node) => {
    node.dataset.marker = "preserved";
  });
  await page
    .getByRole("button", { name: "Close preview", exact: true })
    .focus();
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(media).toHaveAttribute("data-marker", "preserved");
  await expect(
    page.getByRole("button", { name: "Close preview", exact: true }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Active 0", exact: true }).click();
  await expect(media).toHaveCount(0);
  await expect(page.locator("#filter-empty")).toBeVisible();
});

test("confirms early deletion and leaves the other job visible", async ({
  page,
}) => {
  let removed = false;
  await page.route("**/api/jobs", (route) =>
    route.fulfill({ json: removed ? [failed] : [ready, failed] }),
  );
  await page.route(`**/api/jobs/${ready.id}`, (route) => {
    expect(route.request().method()).toBe("DELETE");
    removed = true;
    return route.fulfill({ status: 204 });
  });
  await page.goto("/");
  await page
    .locator(`[data-id="${ready.id}"]`)
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Delete this job?" });
  await expect(dialog.getByRole("button", { name: "Keep" })).toBeFocused();
  await dialog.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("heading", { name: ready.title })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: failed.title })).toBeVisible();
});

test("retries a failed job with a bounded request key", async ({ page }) => {
  await page.route(`**/api/jobs/${failed.id}/retry`, (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers()["idempotency-key"]).toMatch(
      /^[a-f0-9-]{36}$/,
    );
    return route.fulfill({
      status: 202,
      json: { ...failed, id: "c".repeat(32), state: "queued", error: null },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator('[data-state="queued"]')).toBeVisible();
  await expect(page.locator('[data-state="failed"]')).toBeVisible();
});

test("renews an expired browser session and recovers the library", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/jobs", (route) =>
    ++calls === 1
      ? route.fulfill({ status: 401, json: { detail: "session_required" } })
      : route.fulfill({ json: [ready] }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: ready.title })).toBeVisible();
  await expect(page.locator("#connection-notice")).toBeHidden();
  expect(calls).toBeGreaterThanOrEqual(2);
});

test("remembers format and quality but never the source URL", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Audio MP3").check();
  await page.getByLabel("Quality", { exact: true }).selectOption("320");
  await page.getByLabel("Video link").fill("https://youtu.be/BaW_jenozKc");
  await page.reload();
  await expect(page.getByLabel("Audio MP3")).toBeChecked();
  await expect(page.getByLabel("Quality", { exact: true })).toHaveValue("320");
  await expect(page.getByLabel("Video link")).toHaveValue("");
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(
    "BaW_jenozKc",
  );
});

test("shows real guest limits and does not offer unconfigured social login", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("#budget-remaining")).toHaveText("2 of 3 left");
  await expect(page.locator('#quality option[value="1080"]')).toHaveCount(0);
  await page.getByRole("button", { name: "Account & limits" }).click();
  const dialog = page.getByRole("dialog", { name: "Account & limits" });
  await expect(dialog).toContainText("Sign-in is not available here yet");
  await expect(
    dialog.getByRole("button", { name: /Continue with/ }),
  ).toHaveCount(0);
  const result = await new AxeBuilder({ page }).analyze();
  expect(
    result.violations.filter((v) => ["serious", "critical"].includes(v.impact)),
  ).toEqual([]);
  await page.screenshot({
    path: `test-results/account-${test.info().project.name}.png`,
  });
});

test("renders account actions and signs out without retaining the account library", async ({
  page,
}) => {
  let loggedIn = true;
  await page.route("**/api/session", (route) =>
    route.fulfill({
      json: loggedIn
        ? {
            ...session,
            account: { name: "Sample user", provider: "google" },
            tier: "free",
          }
        : session,
    }),
  );
  await page.route("**/api/jobs", (route) =>
    route.fulfill({ json: loggedIn ? [ready] : [] }),
  );
  await page.route("**/api/logout?all_devices=true", (route) => {
    loggedIn = false;
    return route.fulfill({ status: 204 });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Sample user" }).click();
  await page.getByRole("button", { name: "Sign out all devices" }).click();
  await expect(
    page.getByRole("button", { name: "Account & limits" }),
  ).toBeVisible();
  await expect(page.locator(".job")).toHaveCount(0);
});

test("reuses an idempotency key after an ambiguous connection failure", async ({
  page,
}) => {
  const keys = [];
  await page.route("**/api/jobs", (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: [] });
    keys.push(route.request().headers()["idempotency-key"]);
    return keys.length === 1
      ? route.abort("failed")
      : route.fulfill({ status: 202, json: ready });
  });
  await page.goto("/");
  await page.getByLabel("Video link").fill("https://youtu.be/BaW_jenozKc");
  await page.getByRole("button", { name: "Prepare download" }).click();
  await expect(page.locator("#form-error")).toBeVisible();
  await page.getByRole("button", { name: "Prepare download" }).click();
  await expect(page.getByRole("heading", { name: ready.title })).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});

test("shows populated library without overflow or serious accessibility issues", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".job")).toHaveCount(2);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const result = await new AxeBuilder({ page }).analyze();
  expect(
    result.violations.filter((v) => ["serious", "critical"].includes(v.impact)),
  ).toEqual([]);
  await page.screenshot({
    path: `test-results/library-${test.info().project.name}.png`,
    fullPage: true,
  });
});

test("shows configured social providers and handles a login outage in the dialog", async ({
  page,
}) => {
  await page.route("**/api/session", (route) =>
    route.fulfill({
      json: { ...session, login_providers: ["google", "facebook"] },
    }),
  );
  await page.route("**/api/auth/google", (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers()["x-requested-with"]).toBe("yt-downloader");
    return route.fulfill({
      status: 503,
      json: { detail: "login_unavailable" },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Account & limits" }).click();
  const google = page.getByRole("button", { name: "Continue with Google" });
  await expect(
    page.getByRole("button", { name: "Continue with Facebook" }),
  ).toBeVisible();
  await google.click();
  await expect(page.locator("#account-error")).toContainText(
    "Sign-in is unavailable",
  );
  await expect(google).toBeEnabled();
});
