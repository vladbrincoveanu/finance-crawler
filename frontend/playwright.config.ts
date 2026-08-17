import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  snapshotDir: './.frontend-design/baselines',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3010',
    trace: 'on-first-retry',
  },
});
