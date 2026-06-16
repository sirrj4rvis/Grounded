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
        
        # -> Click the 'Open live demo →' button to navigate to the interactive app page so the example chips and calibration rail can be used.
        # Open live demo → link
        elem = page.get_by_role('link', name='Open live demo →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 1' chip button to load its example answer and reveal the calibration rail and classification UI.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Move the calibration slider to a lower threshold (set the support-score threshold to 0.50) so the app should reclassify claims and update the calibration percentage.
        # Support-score threshold range field
        elem = page.locator('[id="thr"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("0.50")
        
        # --> Assertions to verify final state
        
        # --> Verify claim support classifications update
        # Assert: Support-score threshold input value is 0.5, confirming the slider change applied.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/input").nth(0)).to_have_attribute("value", "0.5", timeout=15000), "Support-score threshold input value is 0.5, confirming the slider change applied."
        # Assert: Third claim shows a support score of 0.84 (above the 0.5 threshold), indicating it is treated as supported.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[3]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.84", timeout=15000), "Third claim shows a support score of 0.84 (above the 0.5 threshold), indicating it is treated as supported."
        
        # --> Verify the groundedness percentage updates
        # Assert: The groundedness percentage initially shows 34.9%.
        await expect(page.locator("xpath=/html/body/div[1]/div/span[2]/span/span[2]").nth(0)).to_have_text("34.9%", timeout=15000), "The groundedness percentage initially shows 34.9%."
        # Assert: The groundedness percentage updated to 13.1% after adjusting the threshold.
        await expect(page.locator("xpath=/html/body/div[1]/div/span[2]/span/span[4]").nth(0)).to_have_text("13.1%", timeout=15000), "The groundedness percentage updated to 13.1% after adjusting the threshold."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    