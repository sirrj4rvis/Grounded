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
        
        # -> Click the 'Open live demo →' button to open the live demo app so the annotated answer view can be accessed.
        # Open live demo → link
        elem = page.get_by_role('link', name='Open live demo →', exact=True)
        await elem.click(timeout=10000)
        
        # -> click
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'annotated' button to switch to the annotated answer view and verify unsupported content appears inline and is struck through.
        # annotated button
        elem = page.locator('[id="vAnno"]')
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the annotated answer is displayed
        await page.locator("xpath=/html/body/div[2]/div[5]/div[3]/h2/span/button[2]").nth(0).scroll_into_view_if_needed()
        # Assert: The annotated tab button is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[3]/h2/span/button[2]").nth(0)).to_be_visible(timeout=15000), "The annotated tab button is visible."
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The annotated answer content is visible on the page.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_be_visible(timeout=15000), "The annotated answer content is visible on the page."
        
        # --> Verify unsupported content is shown inline in the answer
        # Assert: The sentence about Alaska and Mississippi is visible inline in the annotated answer.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[2]").nth(0)).to_contain_text("The specific amount of pay varies by location, with the highest average pay in Alaska ($23.70 per hour or $49,400 per year) and the lowest average pay in Mississippi ($18.60 per hour or $38,900 per year).", timeout=15000), "The sentence about Alaska and Mississippi is visible inline in the annotated answer."
        # Assert: The sentence stating the passages do not provide specific payment information is visible inline in the annotated answer.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[4]").nth(0)).to_contain_text("However, the passages do not provide specific information on how automotive technicians get paid or their typical salaries.", timeout=15000), "The sentence stating the passages do not provide specific payment information is visible inline in the annotated answer."
        # Assert: The sentence indicating inability to answer based on the passages is visible inline in the annotated answer.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[5]").nth(0)).to_contain_text("Therefore, I am unable to answer the question based on the given passages.", timeout=15000), "The sentence indicating inability to answer based on the passages is visible inline in the annotated answer."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    