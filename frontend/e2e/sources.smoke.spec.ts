import { expect, test } from '@playwright/test';

test('shows live samples from all three crawl sources', async ({ page }) => {
  await page.goto('/sources');

  await expect(page.getByRole('heading', { name: 'Source verification' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Dataroma' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'HedgeFollow' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'ValueInvestorsClub.com' })).toBeVisible();

  await expect(page.getByText('BRK.B', { exact: true })).toBeVisible();
  await expect(page.getByText('HLF', { exact: true })).toBeVisible();
  await expect(page.getByText('BCC', { exact: true })).toBeVisible();
  await expect(page.getByText('Berkshire Hathaway CL B')).toBeVisible();
  await expect(page.getByText('Herbalife Ltd')).toBeVisible();
  await expect(page.getByText('Boise Cascade')).toBeVisible();

  await expect(page.getByText(/Public route: \/holdings\/dataroma/)).toBeVisible();
  await expect(page.getByRole('link', { name: /Open original source record for Dataroma/i }))
    .toHaveAttribute('href', /dataroma\.com/);
  await expect(page.getByRole('link', { name: /Open original source record for HedgeFollow/i }))
    .toHaveAttribute('href', /hedgefollow\.com\/funds/);
  await expect(page.getByRole('link', { name: /Open original source record for ValueInvestorsClub\.com/i }))
    .toHaveAttribute('href', /valueinvestorsclub\.com\/idea/);

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('shows live source evidence on the dashboard', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'VIC Analytics Dashboard' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Live crawl evidence' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Dataroma' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'HedgeFollow' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'ValueInvestorsClub.com' })).toBeVisible();

  await expect(page.getByText('BRK.B', { exact: true })).toBeVisible();
  await expect(page.getByText('HLF', { exact: true })).toBeVisible();
  await expect(page.getByText('BCC', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'View full source verification' })).toHaveAttribute('href', '/sources');

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
