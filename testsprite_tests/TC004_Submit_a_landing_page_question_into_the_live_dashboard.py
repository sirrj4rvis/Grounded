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
        
        # -> Fill 'How do automotive technicians get paid?' into the 'Verify your own question…' input on the landing page and click the 'Verify →' button to open the live dashboard.
        # Verify your own question text field
        elem = page.get_by_label('Verify your own question', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("How do automotive technicians get paid?")
        
        # -> Fill 'How do automotive technicians get paid?' into the 'Verify your own question…' input on the landing page and click the 'Verify →' button to open the live dashboard.
        # Verify → button
        elem = page.get_by_role('button', name='Verify →', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the live dashboard opens with the question prefilled
        # Assert: The dashboard URL includes the submitted question as the q= query parameter.
        await expect(page).to_have_url(re.compile("app\\?q=How\\+do\\+automotive\\+technicians\\+get\\+paid%3F"), timeout=15000), "The dashboard URL includes the submitted question as the q= query parameter."
        # Assert: The Ask input on the dashboard is prefilled with the submitted question.
        await expect(page.locator("xpath=/html/body/div[2]/form/input").nth(0)).to_have_value("How do automotive technicians get paid?", timeout=15000), "The Ask input on the dashboard is prefilled with the submitted question."
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    