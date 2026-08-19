import { test, expect } from '@playwright/test';

const viewports = [
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1280', width: 1280, height: 720 },
];

for (const viewport of viewports) {
  test(`source verification is legible at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: /Source verification/i })).toBeVisible();
    await expect(page.getByText('/articles')).toBeVisible();
    await expect(page.getByText('/holdings/dataroma')).toBeVisible();
    await expect(page.getByText('/holdings/hedgefollow')).toBeVisible();
    await expect(page).toHaveScreenshot(`sources-routes-${viewport.name}.png`, { fullPage: true });
  });

  test(`product dashboard exposes telemetry at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /VIC Analytics Dashboard/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /open ingestion telemetry/i })).toHaveAttribute(
      'href',
      'http://localhost:3001/d/vic-ingestion',
    );
    await expect(page).toHaveScreenshot(`home-telemetry-${viewport.name}.png`, { fullPage: true });
  });
}
