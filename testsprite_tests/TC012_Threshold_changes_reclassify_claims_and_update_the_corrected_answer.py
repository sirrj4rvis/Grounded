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
        
        # -> Navigate to the application demo page by visiting /app (open the app page at /app).
        await page.goto("http://localhost:8000/app")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Click the 'example 1' button to load a precomputed example and reveal the verification UI (results panel and support-threshold control).
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Set the 'threshold' support-score slider in the Calibration panel (currently showing 'threshold 0.77') to 0.30 so the claim classifications, groundedness, and corrected answer update.
        # Support-score threshold range field
        elem = page.locator('[id="thr"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("0.30")
        
        # --> Assertions to verify final state
        
        # --> Verify claim classifications update after the threshold changes
        # Assert: Claim 1 shows a support score of 0.97.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.97", timeout=15000), "Claim 1 shows a support score of 0.97."
        # Assert: Claim 2 shows a support score of 0.01.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[2]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.01", timeout=15000), "Claim 2 shows a support score of 0.01."
        # Assert: Claim 3 shows a support score of 0.84.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[3]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.84", timeout=15000), "Claim 3 shows a support score of 0.84."
        # Assert: Claim 4 shows a support score of 0.29.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[4]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.29", timeout=15000), "Claim 4 shows a support score of 0.29."
        # Assert: Claim 5 shows a support score of 0.03.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[5]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.03", timeout=15000), "Claim 5 shows a support score of 0.03."
        
        # --> Verify the groundedness result and corrected answer update
        # Assert: Support-threshold slider is set to 0.30.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/input").nth(0)).to_have_value("0.3", timeout=15000), "Support-threshold slider is set to 0.30."
        # Assert: Claim 1 shows a support score of 0.97 (supported).
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.97", timeout=15000), "Claim 1 shows a support score of 0.97 (supported)."
        # Assert: Claim 3 shows a support score of 0.84 (supported).
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[3]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.84", timeout=15000), "Claim 3 shows a support score of 0.84 (supported)."
        # Assert: Corrected answer includes the kept claim sentence about how automotive technicians can be paid.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_contain_text("Based on the provided passages, automotive technicians can get paid in different ways, including hourly and commission-based pay.", timeout=15000), "Corrected answer includes the kept claim sentence about how automotive technicians can be paid."
        # Assert: Corrected answer includes the kept claim sentence about higher pay in related industries (aerospace).
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[3]").nth(0)).to_contain_text("Additionally, some automotive technicians may earn more working in related industries such as aerospace products and parts manufacturing, which pays an average of $32 per hour or $66,300 per year.", timeout=15000), "Corrected answer includes the kept claim sentence about higher pay in related industries (aerospace)."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    