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
        
        # -> Click the 'Open live demo →' button to open the interactive app where a custom question can be submitted.
        # Open live demo → link
        elem = page.get_by_role('link', name='Open live demo →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the question field with an out-of-corpus question ('Who invented the jet engine?') and click the 'Ask' button to submit it for verification, then wait for the response.
        # Ask a question text field
        elem = page.locator('[id="q"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Who invented the jet engine?")
        
        # -> Fill the question field with an out-of-corpus question ('Who invented the jet engine?') and click the 'Ask' button to submit it for verification, then wait for the response.
        # Ask button
        elem = page.locator('[id="go"]')
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the dashboard shows an abstaining answer
        # Assert: The dashboard shows an abstaining answer message in the claim title.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div").nth(0)).to_have_attribute("title", "I don't know based on the provided context.  \u00b7  score 0.06", timeout=15000), "The dashboard shows an abstaining answer message in the claim title."
        
        # --> Verify claim-by-claim verification results are displayed for the submitted question
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div").nth(0).scroll_into_view_if_needed()
        # Assert: A claim-by-claim result block for the submitted question is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div").nth(0)).to_be_visible(timeout=15000), "A claim-by-claim result block for the submitted question is visible."
        # Assert: A claim support score of 0.06 is displayed.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.06", timeout=15000), "A claim support score of 0.06 is displayed."
        await page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div/button").nth(0).scroll_into_view_if_needed()
        # Assert: An evidence button is present to inspect the checked passage for the claim.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div/button").nth(0)).to_be_visible(timeout=15000), "An evidence button is present to inspect the checked passage for the claim."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    