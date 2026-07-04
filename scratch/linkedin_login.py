import os
import sys
import json
import asyncio
from loguru import logger

# Configure Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Force stdout to UTF-8
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LI_COOKIES = os.path.join(PROJECT_ROOT, "linkedin_cookies.json")
PROXY = "http://172.30.10.10:3128"

async def main():
    from playwright.async_api import async_playwright

    logger.info("=====================================================================")
    logger.info("LinkedIn Interactive Login Setup Script")
    logger.info("=====================================================================")
    logger.info("This script will open Google Chrome on your screen so you can log in.")
    logger.info("After logging in successfully, press ENTER in this terminal to save cookies.")
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
        logger.info("Navigating to LinkedIn login page...")
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)

        print("\n--> PLEASE LOG IN IN THE CHROME WINDOW NOW.")
        print("--> AFTER YOU SUCCESSFULLY LOG IN AND REACH THE FEED PAGE,")
        input("--> PRESS [ENTER] HERE IN THIS TERMINAL TO SAVE YOUR SESSION COOKIES...")

        # Save cookies
        cookies = await ctx.cookies()
        with open(LI_COOKIES, "w", encoding="utf-8") as f:
            json.dump({"cookies": cookies}, f, indent=2, ensure_ascii=False)
            
        logger.success(f"Successfully saved {len(cookies)} cookies to {LI_COOKIES}!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
