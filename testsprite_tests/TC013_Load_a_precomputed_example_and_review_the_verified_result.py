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
        
        # -> Navigate to the dashboard page at '/app' (open the app dashboard page so example chips and their precomputed verification results can be selected).
        await page.goto("http://localhost:8000/app")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Click the 'example 1' example chip to load its precomputed verification results and corrected answer.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify claim-by-claim verification results are displayed
        # Assert: A claim support score of "0.97" is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.97", timeout=15000), "A claim support score of \"0.97\" is visible."
        # Assert: A claim support score of "0.84" is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[3]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.84", timeout=15000), "A claim support score of \"0.84\" is visible."
        # Assert: A claim support score of "0.01" is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[2]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.01", timeout=15000), "A claim support score of \"0.01\" is visible."
        await page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0).scroll_into_view_if_needed()
        # Assert: An evidence toggle button is present for inspecting claim evidence.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/button").nth(0)).to_be_visible(timeout=15000), "An evidence toggle button is present for inspecting claim evidence."
        
        # --> Verify a corrected answer is displayed
        # Assert: The corrected answer's opening sentence is displayed.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_have_text("Based on the provided passages, automotive technicians can get paid in different ways, including hourly and commission-based pay.", timeout=15000), "The corrected answer's opening sentence is displayed."
        # Assert: The corrected answer's follow-up sentence is displayed.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[3]").nth(0)).to_have_text("Additionally, some automotive technicians may earn more working in related industries such as aerospace products and parts manufacturing, which pays an average of $32 per hour or $66,300 per year.", timeout=15000), "The corrected answer's follow-up sentence is displayed."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    