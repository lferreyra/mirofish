import { test, expect } from '@playwright/test';

test.describe('Research Topic Mode', () => {

  test('should show tab switcher on home page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Scroll to the dashboard section so the console is visible
    const dashboard = page.locator('.dashboard-section');
    await dashboard.scrollIntoViewIfNeeded();

    // The tab buttons use class .mode-tab and contain Chinese text
    const fileTab = page.locator('.mode-tab', { hasText: '文件上传' });
    const researchTab = page.locator('.mode-tab', { hasText: '研究课题' });

    await expect(fileTab).toBeVisible({ timeout: 15000 });
    await expect(researchTab).toBeVisible();
  });

  test('should switch to research mode when clicking research tab', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const dashboard = page.locator('.dashboard-section');
    await dashboard.scrollIntoViewIfNeeded();

    // Click the research tab
    const researchTab = page.locator('.mode-tab', { hasText: '研究课题' });
    await researchTab.waitFor({ state: 'visible', timeout: 15000 });
    await researchTab.click();

    // Research textarea should now be visible
    const researchTextarea = page.locator('.research-textarea');
    await expect(researchTextarea).toBeVisible({ timeout: 5000 });

    // Depth selector buttons should be visible (Quick, Deep, Full Research)
    const quickBtn = page.locator('.depth-btn', { hasText: 'Quick' });
    const deepBtn = page.locator('.depth-btn', { hasText: 'Deep' });
    const fullBtn = page.locator('.depth-btn', { hasText: 'Full Research' });

    await expect(quickBtn).toBeVisible();
    await expect(deepBtn).toBeVisible();
    await expect(fullBtn).toBeVisible();
  });

  test('should enable submit when research topic and simulation requirement are filled', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const dashboard = page.locator('.dashboard-section');
    await dashboard.scrollIntoViewIfNeeded();

    // Switch to research tab
    const researchTab = page.locator('.mode-tab', { hasText: '研究课题' });
    await researchTab.waitFor({ state: 'visible', timeout: 15000 });
    await researchTab.click();

    // The submit button should be disabled initially
    const submitBtn = page.locator('.start-engine-btn');
    await expect(submitBtn).toBeDisabled();

    // Fill in research topic
    const researchTextarea = page.locator('.research-textarea');
    await researchTextarea.fill('US chip tariff impact on TSMC');

    // Still disabled (simulation requirement not filled)
    await expect(submitBtn).toBeDisabled();

    // Fill in simulation requirement (the .code-input textarea)
    const simulationTextarea = page.locator('.code-input');
    await simulationTextarea.fill('Simulate social media reaction to new chip tariffs');

    // Now the submit button should be enabled
    await expect(submitBtn).toBeEnabled();
  });

  test('file upload tab should still work', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const dashboard = page.locator('.dashboard-section');
    await dashboard.scrollIntoViewIfNeeded();

    // File upload tab should be active by default - upload zone visible
    const fileTab = page.locator('.mode-tab', { hasText: '文件上传' });
    await fileTab.waitFor({ state: 'visible', timeout: 15000 });

    const uploadZone = page.locator('.upload-zone');
    await expect(uploadZone).toBeVisible({ timeout: 5000 });

    // Switch to research and back to file upload
    const researchTab = page.locator('.mode-tab', { hasText: '研究课题' });
    await researchTab.click();

    // Upload zone should be hidden now
    await expect(uploadZone).toBeHidden();

    // Switch back
    await fileTab.click();

    // Upload zone should be visible again
    await expect(uploadZone).toBeVisible();
  });

});
