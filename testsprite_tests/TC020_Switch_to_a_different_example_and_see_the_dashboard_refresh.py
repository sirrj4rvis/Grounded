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
        
        # -> Click the 'Open live demo →' link to open the demo app page (the interactive app at /app).
        # Open live demo → link
        elem = page.get_by_role('link', name='Open live demo →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 1' example chip to load its precomputed verification result and claims.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 2' button to load its precomputed verification result and observe whether the calibration and claim texts update.
        # example 2 button
        elem = page.get_by_role('button', name='example 2', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the displayed verification result updates to a different example
        # Assert: Top claim's title shows the grilling example was loaded.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_have_attribute("title", "To grill a porterhouse steak, follow these steps:\n\n1.  \u00b7  score 0.86", timeout=15000), "Top claim's title shows the grilling example was loaded."
        # Assert: Top claim's support score is 0.86, confirming the displayed verification result updated to the grilling example.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.86", timeout=15000), "Top claim's support score is 0.86, confirming the displayed verification result updated to the grilling example."
        
        # --> Verify the displayed claims change
        # Assert: The claims list shows the 'To grill a porterhouse steak, follow these steps:' heading, indicating the displayed claims updated.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_contain_text("To grill a porterhouse steak, follow these steps:", timeout=15000), "The claims list shows the 'To grill a porterhouse steak, follow these steps:' heading, indicating the displayed claims updated."
        # Assert: A claim support score of '0.86' is visible, confirming the new claim items are displayed.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.86", timeout=15000), "A claim support score of '0.86' is visible, confirming the new claim items are displayed."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    