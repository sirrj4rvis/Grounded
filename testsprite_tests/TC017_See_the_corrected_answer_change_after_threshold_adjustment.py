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
        
        # -> Click the 'Open live demo →' button in the page header to open the demo app (navigate to /app).
        # Open live demo → link
        elem = page.get_by_role('link', name='Open live demo →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 1' button to load the precomputed example chip into the demo and reveal the calibration/claims UI.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Move the calibration threshold slider (the support-score threshold control) to a lower cutoff (set it to 0.50) so the UI recalculates supported claims and updates the corrected answer and calibration display.
        # Support-score threshold range field
        elem = page.locator('[id="thr"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("0.5")
        
        # -> Temporarily change the support-score threshold slightly and restore it to 0.50 to force recalculation, then verify the corrected answer text and the calibration/threshold display update accordingly.
        # Support-score threshold range field
        elem = page.locator('[id="thr"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("0.51")
        
        # -> Temporarily change the support-score threshold slightly and restore it to 0.50 to force recalculation, then verify the corrected answer text and the calibration/threshold display update accordingly.
        # Support-score threshold range field
        elem = page.locator('[id="thr"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("0.50")
        
        # --> Assertions to verify final state
        
        # --> Verify the corrected answer changes
        # Assert: The corrected answer displays the updated corrected answer text.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_have_text("Based on the provided passages, automotive technicians can get paid in different ways, including hourly and commission-based pay. Additionally, some automotive technicians may earn more working in related industries such as aerospace products and parts manufacturing, which pays an average of $32 per hour or $66,300 per year.", timeout=15000), "The corrected answer displays the updated corrected answer text."
        
        # --> Verify the updated groundedness result is displayed
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The corrected answer block is visible on the page.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_be_visible(timeout=15000), "The corrected answer block is visible on the page."
        await page.locator("xpath=/html/body/div[2]/div[5]/div[3]/h2/span/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The 'corrected' view button is visible, indicating corrected answers are being shown.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[3]/h2/span/button[1]").nth(0)).to_be_visible(timeout=15000), "The 'corrected' view button is visible, indicating corrected answers are being shown."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    