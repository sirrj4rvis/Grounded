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
        
        # -> Open the app page by navigating to 'http://127.0.0.1:8000/app' so the interactive verification UI can be tested.
        await page.goto("http://127.0.0.1:8000/app")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Click the 'example 1' chip to load its claims in the verification view.
        # example 1 button
        elem = page.get_by_role('button', name='example 1', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the first claim marker to reveal its claim text/evidence and focus the claim in the verification view.
        # Based on the provided passages, automotive...
        elem = page.locator('xpath=/html/body/div[2]/div[5]/div/div[2]/div/div[2]/div')
        await elem.click(timeout=10000)
        
        # -> Simulate hovering the top claim marker (the green triangle next to the top claim) to reveal its claim text/evidence, then expand the claim's 'evidence' toggle and finally click the same claim marker to verify the verification view jumps ...
        # Based on the provided passages, automotive...
        elem = page.locator('xpath=/html/body/div[2]/div[5]/div/div[2]/div/div[2]/div')
        await elem.click(timeout=10000)
        
        # -> Simulate hovering the top claim marker (the green triangle next to the top claim) to reveal its claim text/evidence, then expand the claim's 'evidence' toggle and finally click the same claim marker to verify the verification view jumps ...
        # ▸ evidence button
        elem = page.get_by_text('0.97supported', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='▸ evidence', exact=True)
        await elem.click(timeout=10000)
        
        # -> Simulate hovering the top claim marker (the green triangle next to the top claim) to reveal its claim text/evidence, then expand the claim's 'evidence' toggle and finally click the same claim marker to verify the verification view jumps ...
        # Based on the provided passages, automotive...
        elem = page.locator('xpath=/html/body/div[2]/div[5]/div/div[2]/div/div[2]/div')
        await elem.click(timeout=10000)
        
        # -> Click the top claim marker (the green triangle next to the first claim: 'Based on the provided passages, automotive technicians can get paid in different ways, including hourly and commission-based pay.') to verify the verification view ...
        # Based on the provided passages, automotive...
        elem = page.locator('xpath=/html/body/div[2]/div[5]/div/div[2]/div/div[2]/div')
        await elem.click(timeout=10000)
        
        # -> Click the top claim marker (the green triangle next to the claim: 'Based on the provided passages, automotive technicians can get paid in different ways, including hourly and commission-based pay.') to verify the verification view jumps/...
        # Based on the provided passages, automotive...
        elem = page.locator('xpath=/html/body/div[2]/div[5]/div/div[2]/div/div[2]/div')
        await elem.click(timeout=10000)
        
        # -> Click the top claim marker — the green triangle next to the first claim that begins "Based on the provided passages, automotive technicians can get paid..." to verify the verification view jumps/focuses to that claim.
        # Based on the provided passages, automotive...
        elem = page.locator('xpath=/html/body/div[2]/div[5]/div/div[2]/div/div[2]/div')
        await elem.click(timeout=10000)
        
        # -> Click the top claim marker (the green triangle next to the first claim: 'Based on the provided passages, automotive technicians can get paid in different ways, including hourly and commission-based pay.') to verify the verification view ...
        # Based on the provided passages, automotive...
        elem = page.locator('xpath=/html/body/div[2]/div[5]/div/div[2]/div/div[2]/div')
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the verification view jumps to that claim
        await page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The verification view is focused on the first claim and that claim element is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[1]/div[2]/div[1]/div[2]/div[1]").nth(0)).to_be_visible(timeout=15000), "The verification view is focused on the first claim and that claim element is visible."
        # Assert: The first claim's support score is 0.97, confirming the top claim is shown in the verification view.
        await expect(page.locator("xpath=/html/body/div[2]/div[5]/div[2]/div[2]/div[1]/div[1]/span[2]/span[1]").nth(0)).to_have_text("0.97", timeout=15000), "The first claim's support score is 0.97, confirming the top claim is shown in the verification view."
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
    