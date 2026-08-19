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
  test(`Dataroma holdings is legible at ${viewport.name}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/holdings/dataroma');
    await expect(page.getByRole('heading', { name: /Dataroma holdings/i })).toBeVisible();
    await expect(page.getByText(/Public view · reviewed identities only/i)).toBeVisible();
    await expect(page.getByLabel('Loading curated holdings')).toHaveCount(0);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      viewport.width,
    );
    await expect.poll(() => page.evaluate(findHorizontalOverflow, viewport.width)).toEqual([]);
    await expect(page).toHaveScreenshot(`holdings-dataroma-${viewport.name}.png`, {
      fullPage: true,
      mask: [page.getByTestId('footer-year')],
    });
  });
}
