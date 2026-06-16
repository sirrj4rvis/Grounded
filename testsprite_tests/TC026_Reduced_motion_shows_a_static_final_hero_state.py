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
        
        # --> Assertions to verify final state
        
        # --> Verify the hero verification result is displayed statically
        await page.locator("xpath=/html/body/header/div/div[2]/div[1]/button").nth(0).scroll_into_view_if_needed()
        # Assert: The replay button is visible, indicating the hero is in its settled final state with replay available.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[1]/button").nth(0)).to_be_visible(timeout=15000), "The replay button is visible, indicating the hero is in its settled final state with replay available."
        await page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[4]").nth(0).scroll_into_view_if_needed()
        # Assert: The first claim's verification score '0.97' is visible, showing the final verification result.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[4]").nth(0)).to_be_visible(timeout=15000), "The first claim's verification score '0.97' is visible, showing the final verification result."
        await page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[3]/span[4]").nth(0).scroll_into_view_if_needed()
        # Assert: A dropped claim score '0.01' is visible, confirming the final dropped outcome is shown.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[3]/span[4]").nth(0)).to_be_visible(timeout=15000), "A dropped claim score '0.01' is visible, confirming the final dropped outcome is shown."
        
        # --> Verify the final groundedness outcome is visible without an active animation
        # Assert: The first claim's verification score '0.97' is visible, showing the final verification result.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[4]").nth(0)).to_have_text("0.97", timeout=15000), "The first claim's verification score '0.97' is visible, showing the final verification result."
        # Assert: The second claim's verification score '0.01' is visible, indicating its dropped final score.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[3]/span[4]").nth(0)).to_have_text("0.01", timeout=15000), "The second claim's verification score '0.01' is visible, indicating its dropped final score."
        await page.locator("xpath=/html/body/header/div/div[2]/div[1]/button").nth(0).scroll_into_view_if_needed()
        # Assert: The replay button is visible, indicating the hero is in its final (static) state with replay available.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[1]/button").nth(0)).to_be_visible(timeout=15000), "The replay button is visible, indicating the hero is in its final (static) state with replay available."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    