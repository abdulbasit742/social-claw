import os
import sys
import json
import asyncio
from playwright.async_api import async_playwright

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LI_COOKIES = os.path.join(project_root, "linkedin_cookies.json")
PROXY = "http://172.30.10.10:3128"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        if os.path.exists(LI_COOKIES):
            with open(LI_COOKIES, encoding="utf-8") as f:
                cookies_data = json.load(f)
                if cookies_data.get("cookies"):
                    await ctx.add_cookies(cookies_data["cookies"])
                    print("Loaded cookies.")
        page = await ctx.new_page()
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        url = page.url
        print(f"Current URL: {url}")
        await page.screenshot(path="li_feed_test.png")
        print("Screenshot saved to li_feed_test.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
