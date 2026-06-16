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
        
        # -> Enter the question "How do automotive technicians get paid?" into the question field labeled "Verify your own question…" and click the "Verify →" button to submit it.
        # Verify your own question text field
        elem = page.get_by_label('Verify your own question', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("How do automotive technicians get paid?")
        
        # -> Enter the question "How do automotive technicians get paid?" into the question field labeled "Verify your own question…" and click the "Verify →" button to submit it.
        # Verify → button
        elem = page.get_by_role('button', name='Verify →', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify claim-by-claim verdicts are displayed
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div").nth(0).scroll_into_view_if_needed()
        # Assert: The claim-by-claim verdict entry 'I don't know based on the provided context.' is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div").nth(0)).to_be_visible(timeout=15000), "The claim-by-claim verdict entry 'I don't know based on the provided context.' is visible."
        # Assert: The claim support score '0.05' for the verdict is displayed.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div/div[1]/span[2]/span[1]").nth(0)).to_contain_text("0.05", timeout=15000), "The claim support score '0.05' for the verdict is displayed."
        
        # --> Verify a corrected answer is displayed
        await page.locator("xpath=/html/body/div[2]/div[5]/div[3]/h2/span/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The corrected tab is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[3]/h2/span/button[1]").nth(0)).to_be_visible(timeout=15000), "The corrected tab is visible."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    