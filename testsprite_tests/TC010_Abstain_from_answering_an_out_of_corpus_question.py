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
        
        # -> Fill the 'Verify your own question…' field with an out-of-corpus question and click the 'Verify →' button to submit it.
        # Verify your own question text field
        elem = page.get_by_label('Verify your own question', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("What is the capital of Atlantis?")
        
        # -> Fill the 'Verify your own question…' field with an out-of-corpus question and click the 'Verify →' button to submit it.
        # Verify → button
        elem = page.get_by_role('button', name='Verify →', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify an abstention message is displayed
        # Assert: An abstention message saying "I don't know based on the provided context." is displayed.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div").nth(0)).to_contain_text("I don't know based on the provided context.", timeout=15000), "An abstention message saying \"I don't know based on the provided context.\" is displayed."
        
        # --> Verify no grounded answer is presented
        # Assert: Corrected/claim answer area shows an abstention message instead of a grounded answer.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div").nth(0)).to_have_attribute("title", "I don't know based on the provided context.  \u00b7  score 0.11", timeout=15000), "Corrected/claim answer area shows an abstention message instead of a grounded answer."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    