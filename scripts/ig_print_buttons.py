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
        
        # Find all divs, buttons, anchors with "Log in" or "Log In" text
        elements = await page.query_selector_all("button, div, a, input")
        print(f"Inspecting elements:")
        for idx, el in enumerate(elements):
            text = await el.text_content()
            text = text.strip() if text else ""
            if "log in" in text.lower():
                tag = await el.evaluate("el => el.tagName")
                class_attr = await el.get_attribute("class")
                type_attr = await el.get_attribute("type")
                print(f"Index {idx}: <{tag} class='{class_attr}' type='{type_attr}'> Text: '{text[:50]}'")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
