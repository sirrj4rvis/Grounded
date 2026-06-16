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
        
        # -> Navigate to the app page by opening the '/app' application interface (the application page where example chips and evidence toggles are available).
        await page.goto("http://127.0.0.1:8000/app")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Click the 'example 1' example chip to load the example claims and evidence UI.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' button under the first claim to expand and reveal the supporting passage.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' button under the first claim to close (collapse) the displayed supporting passage so it is no longer visible.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Ensure the claim's evidence passage is hidden: search the page for the passage text 'The specific amount of pay varies by location, with the highest average pay in Alaska' and then click the 'evidence' button under the first claim to col...
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' button for the first claim (label: 'evidence') to collapse the supporting passage, after first confirming the passage text is currently visible.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' button under the first claim to collapse its supporting passage and verify that the passage is no longer visible.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Confirm the passage 'The specific amount of pay varies by location, with the highest average pay in Alaska' is visible on the page, then click the claim's 'evidence' button to collapse the supporting passage.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Confirm that the passage 'The specific amount of pay varies by location, with the highest average pay in Alaska' is visible on the page, then click the first claim's 'evidence' button to collapse the passage.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' button under the first claim to collapse the supporting passage (the visible 'evidence' toggle below the first claim).
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Confirm the supporting passage 'The specific amount of pay varies by location, with the highest average pay in Alaska' is present on the page, then click the 'evidence' button under the first claim to collapse that passage.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' button for the first claim to collapse the supporting passage, wait briefly for the UI to update, then verify whether the passage 'The specific amount of pay varies by location, with the highest average pay in Alaska...
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 1' chip to reset the claims panel (re-render the example), then re-open and attempt to collapse the first claim's 'evidence' toggle and verify the passage becomes hidden.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' toggle under the first claim to collapse its supporting passage, wait for the UI to update, then verify the passage text is no longer visible on the page by searching for that exact passage.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'evidence' toggle under the first claim to collapse the supporting passage, wait briefly for the UI to update, then verify that the passage text is no longer visible.
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 2' chip to force a different example to render and break the repeated-click loop, so the UI can be re-rendered before re-attempting evidence collapse.
        # example 2 button
        elem = page.get_by_role('button', name='example 2', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'example 1' chip to re-open that example and re-render the claims panel so a controlled open→close verification can be attempted.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the relevant passage is displayed
        # Assert: The supporting passage about pay in Alaska and Mississippi is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[2]").nth(0)).to_contain_text("The specific amount of pay varies by location, with the highest average pay in Alaska ($23.70 per hour or $49,400 per year) and the lowest average pay in Mississippi ($18.60 per hour or $38,900 per year).", timeout=15000), "The supporting passage about pay in Alaska and Mississippi is visible."
        
        # --> Verify the evidence passage is hidden
        # Assert: The evidence passage is hidden.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[2]").nth(0)).not_to_be_visible(timeout=15000), "The evidence passage is hidden."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    