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
        
        # -> click
        # automotive pay link
        elem = page.get_by_role('link', name='automotive pay', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 1' chip (the example button labelled 'example 1') to load the example into the live dashboard.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the live dashboard opens with an example loaded
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The dashboard shows the loaded example's top claim text.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_be_visible(timeout=15000), "The dashboard shows the loaded example's top claim text."
        # Assert: The top claim displays the expected support score '0.97'.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.97", timeout=15000), "The top claim displays the expected support score '0.97'."
        await page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0).scroll_into_view_if_needed()
        # Assert: An evidence toggle is present for the top claim, indicating claim-by-claim results are loaded.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0)).to_be_visible(timeout=15000), "An evidence toggle is present for the top claim, indicating claim-by-claim results are loaded."
        
        # --> Verify claim-by-claim verification results are displayed
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: A claim tile is visible showing the top claim.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_be_visible(timeout=15000), "A claim tile is visible showing the top claim."
        # Assert: The top claim displays a support score of 0.97.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.97", timeout=15000), "The top claim displays a support score of 0.97."
        await page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0).scroll_into_view_if_needed()
        # Assert: An evidence toggle button is present for the claim.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0)).to_be_visible(timeout=15000), "An evidence toggle button is present for the claim."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    