import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/session", (route) =>
    route.fulfill({
      json: {
        max_duration_seconds: 7200,
        max_file_bytes: 524288000,
        retention_seconds: 3600,
        ready: true,
      },
    }),
  );
  await page.route("**/api/jobs", (route) => route.fulfill({ json: [] }));
});

test("submits an MP3 request and shows the finished file", async ({ page }) => {
  let job = null;
  await page.route("**/api/jobs", async (route) => {
    if (route.request().method() === "POST") {
      expect(route.request().postDataJSON()).toEqual({
        url: "https://youtu.be/BaW_jenozKc",
        kind: "mp3",
        quality: 192,
      });
      expect(route.request().headers()["x-requested-with"]).toBe(
        "yt-downloader",
      );
      job = {
        id: "a".repeat(32),
        title: "<img src=x onerror=alert(1)>",
        kind: "mp3",
        quality: 192,
        state: "complete",
        progress: 100,
        file_bytes: 102400,
        created_at: Date.now() / 1000,
        expires_at: Date.now() / 1000 + 3600,
      };
      return route.fulfill({ status: 202, json: job });
    }
    return route.fulfill({ json: job ? [job] : [] });
  });
  await page.goto("/");
  await page.getByLabel("Jazyk / Language").selectOption("en");
  await page.getByLabel("YouTube link").fill("https://youtu.be/BaW_jenozKc");
  await page.getByLabel("Audio MP3").check();
  await page.getByRole("button", { name: "Prepare download" }).click();
  await expect(page.getByRole("link", { name: "Download MP3" })).toBeVisible();
  await expect(
    page.getByText("<img src=x onerror=alert(1)>", { exact: true }),
  ).toBeVisible();
  expect(await page.locator(".job img").count()).toBe(0);
});

test("shows a useful rate-limit error and allows retry", async ({ page }) => {
  await page.route("**/api/jobs", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 429, json: { detail: "rate_limit" } })
      : route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await page.getByLabel("Jazyk / Language").selectOption("en");
  await page.getByLabel("YouTube link").fill("https://youtu.be/BaW_jenozKc");
  await page.getByRole("button", { name: "Prepare download" }).click();
  await expect(page.getByRole("alert")).toContainText("Too many requests");
  await expect(
    page.getByRole("button", { name: "Prepare download" }),
  ).toBeEnabled();
});

test("cancels an active job and has no horizontal overflow", async ({
  page,
}) => {
  const job = {
    id: "b".repeat(32),
    title: "Example video",
    kind: "mp4",
    quality: 720,
    state: "downloading",
    progress: 42,
    created_at: Date.now() / 1000,
  };
  await page.route("**/api/jobs", (route) => route.fulfill({ json: [job] }));
  await page.route(`**/api/jobs/${job.id}`, (route) => {
    expect(route.request().method()).toBe("DELETE");
    job.state = "cancelled";
    return route.fulfill({ json: job });
  });
  await page.goto("/");
  await page.getByLabel("Jazyk / Language").selectOption("en");
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText("Cancelled", { exact: true })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("is keyboard accessible and has no serious accessibility findings", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const result = await new AxeBuilder({ page }).analyze();
  expect(
    result.violations.filter((v) => ["serious", "critical"].includes(v.impact)),
  ).toEqual([]);
  await page.screenshot({
    path: `test-results/home-${test.info().project.name}.png`,
    fullPage: true,
  });
});
