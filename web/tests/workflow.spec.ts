import { test, expect } from "@playwright/test";

test("offline comparison, selection, export and numerical replay", async ({
  page,
}) => {
  const errors: string[] = [];
  const external: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const url = route.request().url();
    if (url.startsWith("http") && !url.startsWith("http://127.0.0.1:8000")) {
      external.push(url);
      return route.abort();
    }
    return route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Select 12 knot scenario" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: "Select 10 knot scenario" }),
  ).toContainText("Misses deadline");
  await expect(
    page.getByText("Departure offshore gate", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("workbench.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Select 14 knot scenario" }).click();
  await expect(
    page.getByRole("button", { name: "Select 14 knot scenario" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByLabel("Environmental fixture").selectOption("calm");
  await expect(
    page.getByText("Inputs changed · Compare to update results"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Compare three speeds" }).click();
  await expect(
    page.getByText("Inputs changed · Compare to update results"),
  ).not.toBeVisible();
  await expect(page.getByText("Calm water · Synthetic vessel")).toBeVisible();
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const downloaded = await downloadEvent;
  const saved = await downloaded.path();
  expect(saved).toBeTruthy();
  await page.getByLabel("Import comparison JSON").setInputFiles(saved!);
  await expect(page.getByRole("status")).toContainText(
    "Replay verified · 3 runs recomputed",
  );
  await page.getByLabel("Chart metric").selectOption("cost");
  await expect(
    page.getByRole("img", { name: "Modeled cost over voyage elapsed hours" }),
  ).toBeVisible();
  await expect(page.locator(".maplibregl-canvas")).toBeVisible();
  await expect(
    page.getByText("Departure offshore gate", { exact: true }),
  ).toBeVisible();
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
});

test("validation, alternate route, missing coverage and failed import", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Select 12 knot scenario" }),
  ).toBeVisible();
  await page.getByLabel("Offshore route").selectOption("outer");
  await page.getByRole("button", { name: "Compare three speeds" }).click();
  await expect(page.locator(".map-bottom")).toContainText("Outer passage");
  await page
    .getByRole("spinbutton", { name: "Baseline speed", exact: true })
    .fill("25");
  await page.getByRole("button", { name: "Compare three speeds" }).click();
  expect(
    await page
      .getByRole("spinbutton", { name: "Baseline speed", exact: true })
      .evaluate((el: HTMLInputElement) => el.validity.rangeOverflow),
  ).toBe(true);
  await page
    .getByRole("spinbutton", { name: "Baseline speed", exact: true })
    .fill("12");
  await page.getByLabel("Arrival deadline UTC").fill("2026-09-26T00:00");
  await page
    .getByLabel("Departure UTC", { exact: true })
    .fill("2026-09-22T00:00");
  await page.getByRole("button", { name: "Compare three speeds" }).click();
  await expect(
    page.getByRole("button", { name: "Select 12 knot scenario" }),
  ).toContainText("Missing coverage");
  await page
    .getByLabel("Import comparison JSON")
    .setInputFiles({
      name: "broken.json",
      mimeType: "application/json",
      buffer: Buffer.from('{"bad":true}'),
    });
  await expect(page.getByRole("alert")).toContainText("Import failed");
});

test("mobile layout has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Select 12 knot scenario" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Select 14 knot scenario" }).click();
  await expect(
    page.getByRole("button", { name: "Select 14 knot scenario" }),
  ).toHaveAttribute("aria-pressed", "true");
});
