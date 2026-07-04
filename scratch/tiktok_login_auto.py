import os
import sys
import json
import asyncio
from loguru import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

TT_COOKIES = os.path.join(PROJECT_ROOT, "tiktok_cookies.json")
PROXY = "http://172.30.10.10:3128"

async def main():
    from playwright.async_api import async_playwright

    logger.info("=====================================================================")
    logger.info("TikTok Automatic Cookie Capture Utility")
    logger.info("=====================================================================")
    logger.info("Starting Google Chrome. Please sign in to your TikTok account.")
    logger.info("This script will automatically detect when you log in and save your session.")
    logger.info("=====================================================================")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--start-maximized"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-US"
        )

        page = await ctx.new_page()
        logger.info("Navigating to TikTok login page...")
        await page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded", timeout=60000)

        logger.info("Waiting for user to log in in the opened Chrome window...")
        
        # Loop to check login status
        logged_in = False
        timeout_seconds = 600  # 10 minutes
        interval = 2
        
        for elapsed in range(0, timeout_seconds, interval):
            await page.wait_for_timeout(interval * 1000)
            
            # Check cookies
            cookies = await ctx.cookies()
            has_session = any(c.get("name") == "sessionid" for c in cookies)
            url = page.url
            
            if has_session and "login" not in url:
                logger.success("Login detected via cookies! Saving session...")
                with open(TT_COOKIES, "w", encoding="utf-8") as f:
                    json.dump({"cookies": cookies}, f, indent=2, ensure_ascii=False)
                logger.success(f"Successfully saved {len(cookies)} cookies to {TT_COOKIES}!")
                logged_in = True
                break
                
            if elapsed % 20 == 0:
                logger.info(f"Still waiting... ({elapsed}s/300s elapsed). Current URL: {url}")
                
        if not logged_in:
            logger.error("Timeout reached before successful login detection.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
