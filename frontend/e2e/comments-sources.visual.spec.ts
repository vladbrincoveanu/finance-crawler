import { test, expect } from '@playwright/test';

const viewports = [
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1280', width: 1280, height: 720 },
];

const findHorizontalOverflow = (viewportWidth: number) => Array.from(document.querySelectorAll<HTMLElement>('*'))
  .filter((element) => {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none'
      && style.visibility !== 'hidden'
      && style.opacity !== '0'
      && rect.width > 0
      && rect.height > 0
      && (rect.left < -0.5 || rect.right > viewportWidth + 0.5);
  })
  .map((element) => {
    const rect = element.getBoundingClientRect();
    const identifier = element.dataset.testid ?? element.getAttribute('aria-label') ?? element.tagName.toLowerCase();
    return `${identifier} (${rect.left.toFixed(1)}-${rect.right.toFixed(1)})`;
  });

for (const viewport of viewports) {
  test(`source verification is legible at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: /Source verification/i })).toBeVisible();
    await expect(page.getByText('/articles')).toBeVisible();
    await expect(page.getByText('/holdings/dataroma')).toBeVisible();
    await expect(page.getByText('/holdings/hedgefollow')).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      viewport.width,
    );
    await expect.poll(() => page.evaluate(findHorizontalOverflow, viewport.width)).toEqual([]);
    await expect(page).toHaveScreenshot(`sources-routes-${viewport.name}.png`, {
      fullPage: true,
      mask: [
        page.getByTestId('volatile-crawl-value'),
        page.getByTestId('volatile-crawl-warning'),
        page.getByTestId('footer-year'),
      ],
    });
  });

  test(`product dashboard exposes telemetry at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /VIC Analytics Dashboard/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /open ingestion telemetry/i })).toHaveAttribute(
      'href',
      'http://localhost:3001/d/vic-ingestion',
    );
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      viewport.width,
    );
    await expect.poll(() => page.evaluate(findHorizontalOverflow, viewport.width)).toEqual([]);
    await expect(page).toHaveScreenshot(`home-telemetry-${viewport.name}.png`, {
      fullPage: true,
      mask: [page.getByTestId('footer-year')],
    });
  });
}
