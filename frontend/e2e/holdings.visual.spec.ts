import { test, expect } from '@playwright/test';

const viewports = [
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1280', width: 1280, height: 720 },
];

for (const viewport of viewports) {
  test(`Dataroma holdings is legible at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/holdings/dataroma');
    await expect(page.getByRole('heading', { name: /Dataroma holdings/i })).toBeVisible();
    await expect(page.getByText(/Public view · reviewed identities only/i)).toBeVisible();
    await expect(page.getByLabel('Loading curated holdings')).toHaveCount(0);
    await expect(page).toHaveScreenshot(`holdings-dataroma-${viewport.name}.png`, {
      fullPage: true,
    });
  });
}
