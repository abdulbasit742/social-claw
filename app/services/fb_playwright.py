#!/usr/bin/env python3
"""
Facebook Playwright Service — Full Auto Post
============================================
auto_factory.py yeh module use karta hai for fully automatic FB posting.
"""
import os, sys, json, time, asyncio
from loguru import logger

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FB_COOKIES   = os.path.join(project_root, "fb_cookies.json")
FB_CREDS     = os.path.join(project_root, "fb_credentials.json")

USERNAME = "shazil5506@gmail.com"
PASSWORD = "mouqeem273red"
PROXY    = "http://172.30.10.10:3128"


def _load(path):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f: return json.load(f)
    except: pass
    return {}

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_fb_credentials() -> str:
    """Return 'ok', 'ok-cookies', or 'skipped-missing'"""
    if os.path.exists(FB_COOKIES) and _load(FB_COOKIES).get("cookies"):
        return "ok-cookies"
    creds = _load(FB_CREDS)
    if creds.get("page_access_token") and creds.get("page_id"):
        return "ok"
    return "skipped-missing"


async def _playwright_post(video_path: str, caption: str) -> dict:
    """Core async Playwright post function"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                  "--start-maximized"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-US"
        )

        # Inject saved cookies
        cookies_data = _load(FB_COOKIES)
        if cookies_data.get("cookies"):
            await ctx.add_cookies(cookies_data["cookies"])
            logger.info("[FB] Loaded saved session cookies")

        page = await ctx.new_page()

        # ── 1. Load Facebook ────────────────────────────────
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── 2. Login if needed ──────────────────────────────
        if "login" in page.url or await page.query_selector('input[name="email"]') is not None or await page.query_selector('#email') is not None:
            logger.info(f"[FB] Logging in as {USERNAME}...")
            try:
                await page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
                email_sel = 'input[name="email"], input[type="email"], #email'
                pass_sel  = 'input[name="pass"], input[type="password"], #pass'
                
                await page.wait_for_selector(email_sel, timeout=10000)
                await page.fill(email_sel, USERNAME)
                await page.wait_for_timeout(600)
                await page.fill(pass_sel, PASSWORD)
                await page.wait_for_timeout(600)
                await page.press(pass_sel, 'Enter')
                logger.info("[FB] Login submitted, waiting...")
                await page.wait_for_timeout(9000)
            except Exception as le:
                logger.error(f"[FB] Login error: {le}")

            # Handle checkpoint
            if "checkpoint" in page.url:
                logger.warning("[FB] Checkpoint — waiting 25s for verification...")
                await page.wait_for_timeout(25000)

        # Save fresh cookies only if we reached feed/home successfully
        url = page.url
        is_logged_in = "facebook.com" in url and not any(x in url for x in ["login", "checkpoint", "two_step", "captcha", "recover"])
        if is_logged_in:
            fresh_cookies = await ctx.cookies()
            _save(FB_COOKIES, {"cookies": fresh_cookies, "saved_at": time.time()})
            logger.info(f"[FB] Cookies saved ({len(fresh_cookies)} cookies)")
        else:
            logger.warning("[FB] Not logged in (on login/checkpoint page). Skipping cookie save to prevent overwrite.")

        # ── 3. Go to Reels/Video create page ────────────────
        logger.info("[FB] Opening video upload page...")
        await page.goto("https://www.facebook.com/reels/create", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(6000)

        # Look for file input
        file_input = None
        file_inputs = await page.query_selector_all('input[type="file"]')
        if file_inputs:
            file_input = file_inputs[0]
            logger.info("[FB] Found file input via query_selector_all")
        else:
            # Fallback selectors
            for selector in ['input[type="file"]', 'input[accept*="video"]']:
                file_input = await page.query_selector(selector)
                if file_input:
                    break

        if not file_input:
            logger.error("[FB] Could not find file upload input! Attempting fallback to home feed upload...")
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            file_inputs = await page.query_selector_all('input[type="file"]')
            if file_inputs:
                file_input = file_inputs[0]

        if not file_input:
            logger.error("[FB] File upload input not found anywhere.")
            await browser.close()
            return {"success": False, "error": "File upload input not found on Facebook"}


        # ── 4. Upload video file ─────────────────────────────
        logger.info(f"[FB] Uploading: {os.path.basename(video_path)}")
        await file_input.set_input_files(video_path)
        await page.wait_for_timeout(8000)
        logger.info("[FB] File selected, waiting for upload...")

        # ── 5. Add caption ───────────────────────────────────
        for cap_sel in [
            'div[contenteditable="true"][data-lexical-editor]',
            'div[contenteditable="true"]',
            'textarea[placeholder*="caption"]',
            'textarea[placeholder*="description"]',
            'textarea[aria-label*="caption"]',
        ]:
            cap_field = await page.query_selector(cap_sel)
            if cap_field:
                await cap_field.click()
                await page.wait_for_timeout(500)
                await cap_field.fill(caption)
                logger.info("[FB] Caption added!")
                break

        await page.wait_for_timeout(3000)

        # ── 6. Publish ────────────────────────────────────────
        published = False
        for btn_name in ['Share', 'Post', 'Publish', 'Next']:
            try:
                btn = page.get_by_role('button', name=btn_name)
                if await btn.count() > 0:
                    await btn.first.click()
                    logger.info(f"[FB] Clicked publish button: {btn_name}")
                    await page.wait_for_timeout(20000)
                    published = True
                    break
            except Exception as e:
                logger.warning(f"[FB] Error clicking button {btn_name}: {e}")

        # Fallback button selection
        if not published:
            for pub_sel in ['button[type="submit"]', 'button.share', 'div[role="button"]']:
                try:
                    pub_btns = await page.query_selector_all(pub_sel)
                    for btn in pub_btns:
                        text = await btn.inner_text()
                        if any(w in text.lower() for w in ['share', 'post', 'publish', 'next']):
                            await btn.click()
                            logger.info(f"[FB] Clicked fallback button: {text}")
                            await page.wait_for_timeout(20000)
                            published = True
                            break
                    if published: break
                except: pass

        url = page.url
        logger.info(f"[FB] Final URL: {url}")

        # Save fresh cookies again
        fresh_cookies = await ctx.cookies()
        _save(FB_COOKIES, {"cookies": fresh_cookies, "saved_at": time.time()})

        await browser.close()

        if published:
            return {"success": True, "url": url, "method": "playwright"}
        else:
            return {"success": False, "error": "Could not find publish button"}


def upload_to_facebook_playwright(video_path: str, caption: str) -> dict:
    """Sync wrapper — call from auto_factory.py"""
    if not os.path.exists(video_path):
        logger.error(f"[FB] Video not found: {video_path}")
        return None
    try:
        logger.info("[FB-Playwright] Starting automated Facebook post...")
        result = asyncio.run(_playwright_post(video_path, caption))
        if result.get("success"):
            logger.success(f"[FB] Posted! URL: {result.get('url','')}")
            return result
        else:
            logger.error(f"[FB] Post failed: {result.get('error','')}")
            return None
    except Exception as e:
        logger.error(f"[FB-Playwright] Exception: {e}")
        return None


# ── Quick test ─────────────────────────────────────────────────
if __name__ == "__main__":
    import glob
    # Find a test video
    videos = glob.glob(os.path.join(project_root, "storage", "tasks", "*", "*.mp4"))
    if not videos:
        print("No test video found in storage/tasks/")
        sys.exit(1)
    
    test_video = sorted(videos)[-1]
    test_cap   = "Entrepreneurship insights that will change your perspective! #business #success #motivation"
    print(f"Test video: {test_video}")
    
    result = upload_to_facebook_playwright(test_video, test_cap)
    print("Result:", result)
