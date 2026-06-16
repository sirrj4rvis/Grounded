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
        
        # -> Click the 'Open live demo →' button to open the interactive live verification dashboard.
        # Open live demo → link
        elem = page.get_by_role('link', name='Open live demo →', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the interactive verification dashboard is displayed
        await page.locator("xpath=/html/body/div[2]/form/input").nth(0).scroll_into_view_if_needed()
        # Assert: The dashboard's question input is visible.
        await expect(page.locator("xpath=/html/body/div[2]/form/input").nth(0)).to_be_visible(timeout=15000), "The dashboard's question input is visible."
        await page.locator("xpath=/html/body/div[2]/form/button").nth(0).scroll_into_view_if_needed()
        # Assert: The 'Ask' button is visible.
        await expect(page.locator("xpath=/html/body/div[2]/form/button").nth(0)).to_be_visible(timeout=15000), "The 'Ask' button is visible."
        await page.locator("xpath=/html/body/div[2]/div[1]/span[2]/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The 'example 1' chip is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[1]/span[2]/button[1]").nth(0)).to_be_visible(timeout=15000), "The 'example 1' chip is visible."
        await page.locator("xpath=/html/body/div[2]/div[1]/span[2]/button[2]").nth(0).scroll_into_view_if_needed()
        # Assert: The 'example 2' chip is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[1]/span[2]/button[2]").nth(0)).to_be_visible(timeout=15000), "The 'example 2' chip is visible."
        await page.locator("xpath=/html/body/div[2]/div[1]/span[2]/button[3]").nth(0).scroll_into_view_if_needed()
        # Assert: The 'example 3' chip is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[1]/span[2]/button[3]").nth(0)).to_be_visible(timeout=15000), "The 'example 3' chip is visible."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    