import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://localhost:8000")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Open the app demo page by navigating to the live demo at /app (visit http://127.0.0.1:8000/app).
        await page.goto("http://127.0.0.1:8000/app")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Click the 'example 1' button to load a precomputed example and reveal the claims list, verdicts, support scores, evidence toggles, and the corrected answer area.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the first claim's 'evidence' toggle button to expand and reveal the underlying passage so the evidence box content can be verified.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify claim verdicts and support scores are displayed
        # Assert: Support score 0.01 is visible for the second claim.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[2]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.01", timeout=15000), "Support score 0.01 is visible for the second claim."
        # Assert: Support score 0.84 is visible for the third claim.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[3]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.84", timeout=15000), "Support score 0.84 is visible for the third claim."
        # Assert: Support score 0.29 is visible for the fourth claim.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[4]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.29", timeout=15000), "Support score 0.29 is visible for the fourth claim."
        # Assert: Support score 0.03 is visible for the fifth claim.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[5]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.03", timeout=15000), "Support score 0.03 is visible for the fifth claim."
        
        # --> Verify evidence and a corrected answer are displayed
        await page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0).scroll_into_view_if_needed()
        # Assert: The evidence toggle button for the first claim is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0)).to_be_visible(timeout=15000), "The evidence toggle button for the first claim is visible."
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The corrected answer text is visible on the page.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_be_visible(timeout=15000), "The corrected answer text is visible on the page."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    