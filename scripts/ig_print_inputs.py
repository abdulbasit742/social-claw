import asyncio
from playwright.async_api import async_playwright

PROXY = "http://172.30.10.10:3128"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy={'server': PROXY},
            args=['--no-sandbox', '--start-maximized']
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width':1366,'height':768}
        )
        page = await ctx.new_page()
        
        print("Loading Instagram login page...")
        await page.goto("https://www.instagram.com/accounts/login/", timeout=40000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        inputs = await page.query_selector_all("input")
        print(f"Found {len(inputs)} inputs:")
        for idx, inp in enumerate(inputs):
            html = await inp.evaluate("el => el.outerHTML")
            print(f"{idx}: {html}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
