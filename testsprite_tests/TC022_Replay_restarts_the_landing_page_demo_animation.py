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
        
        # -> Click the '↻ replay' button on the hero demo and observe whether the verification animation restarts and then reaches the completed verification state.
        # ↻ replay button
        elem = page.locator('[id="replay"]')
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the hero verification animation restarts
        await page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The first claim item (label '1') is visible, indicating the hero demo rendered its claim elements after replay.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[1]").nth(0)).to_be_visible(timeout=15000), "The first claim item (label '1') is visible, indicating the hero demo rendered its claim elements after replay."
        await page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[4]").nth(0).scroll_into_view_if_needed()
        # Assert: A verifier score ('0.97') is visible for a claim, showing the verification run produced claim scores after replay.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[4]").nth(0)).to_be_visible(timeout=15000), "A verifier score ('0.97') is visible for a claim, showing the verification run produced claim scores after replay."
        
        # --> Verify the demo reaches a completed verification state again
        # Assert: The hero demo displays the verifier score 0.97, showing a completed verification run.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[2]/span[4]").nth(0)).to_have_text("0.97", timeout=15000), "The hero demo displays the verifier score 0.97, showing a completed verification run."
        # Assert: The hero demo displays the verifier score 0.01, confirming the completed run includes low-scoring claims.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[3]/span[4]").nth(0)).to_have_text("0.01", timeout=15000), "The hero demo displays the verifier score 0.01, confirming the completed run includes low-scoring claims."
        # Assert: The hero demo displays the verifier score 0.84, indicating claim scores are present after replay.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[4]/span[4]").nth(0)).to_have_text("0.84", timeout=15000), "The hero demo displays the verifier score 0.84, indicating claim scores are present after replay."
        # Assert: The hero demo displays the verifier score 0.03, confirming the demo reached its completed verification state again.
        await expect(page.locator("xpath=/html/body/header/div/div[2]/div[3]/div[6]/span[4]").nth(0)).to_have_text("0.03", timeout=15000), "The hero demo displays the verifier score 0.03, confirming the demo reached its completed verification state again."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    