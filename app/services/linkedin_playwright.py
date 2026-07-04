import os, sys, json, time, asyncio
from loguru import logger

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LI_COOKIES   = os.path.join(project_root, "linkedin_cookies.json")
LI_CREDS     = os.path.join(project_root, "linkedin_credentials.json")

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


def check_linkedin_credentials() -> str:
    """Return 'ok' if we have username/password or cookies"""
    if os.path.exists(LI_COOKIES) and _load(LI_COOKIES).get("cookies"):
        return "ok"
    if os.path.exists(LI_CREDS):
        creds = _load(LI_CREDS)
        if creds.get("email") and creds.get("password"):
            return "ok"
    if USERNAME and PASSWORD:
        return "ok"
    return "skipped-missing"


async def _playwright_post(video_path: str = None, image_path: str = None, text: str = None) -> dict:
    """Core async Playwright LinkedIn post function (supports video, image, and text-only)"""
    from playwright.async_api import async_playwright

    media_path = video_path or image_path
    post_text = text or ""

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
        cookies_data = _load(LI_COOKIES)
        if cookies_data.get("cookies"):
            await ctx.add_cookies(cookies_data["cookies"])
            logger.info("[LinkedIn] Loaded saved session cookies")

        page = await ctx.new_page()

        # ── 1. Load LinkedIn ────────────────────────────────
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(3000)

        # ── 2. Login if needed ──────────────────────────────
        if "login" in page.url or await page.query_selector('input[name="session_key"]') is not None or "feed" not in page.url:
            logger.info(f"[LinkedIn] Logging in as {USERNAME}...")
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            try:
                await page.fill('input[name="session_key"]', USERNAME, timeout=20000)
                await page.fill('input[name="session_password"]', PASSWORD, timeout=20000)
                await page.click('button[type="submit"]', timeout=20000)
                await page.wait_for_timeout(6000)
            except Exception as e:
                logger.error(f"[LinkedIn] Login fill error: {e}")
                try:
                    await page.screenshot(path="li_login_error.png")
                    logger.info("[LinkedIn] Saved li_login_error.png screenshot")
                except:
                    pass

            # Check for verification / verification code / pin
            if "checkpoint" in page.url or "challenge" in page.url:
                logger.warning("[LinkedIn] Verification challenge detected! Waiting 30s for manual verification...")
                await page.wait_for_timeout(30000)

        # Save fresh cookies only if we reached feed/home successfully
        url = page.url
        is_logged_in = "linkedin.com" in url and not any(x in url for x in ["login", "checkpoint", "challenge", "verify"])
        if is_logged_in:
            fresh_cookies = await ctx.cookies()
            _save(LI_COOKIES, {"cookies": fresh_cookies, "saved_at": time.time()})
            logger.info(f"[LinkedIn] Cookies saved ({len(fresh_cookies)} cookies)")
        else:
            logger.warning("[LinkedIn] Not logged in (on login/checkpoint page). Skipping cookie save to prevent overwrite.")

        # ── 3. Start a Post ────────────────────────────────
        logger.info("[LinkedIn] Starting post...")
        # Wait for feed page
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Click the "Start a post" or "Video" or "Photo" buttons using multiple locator fallbacks
        clicked = False
        
        # Fallback 1: If we have an image, try to click the Photo button on feed directly
        if image_path:
            photo_btn = page.get_by_text("Photo", exact=True).first
            if await photo_btn.count() > 0:
                try:
                    await photo_btn.click()
                    logger.info("[LinkedIn] Clicked Photo button directly on feed")
                    clicked = True
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.warning(f"[LinkedIn] Direct Photo click failed: {e}")
                    
        # Fallback 2: If we have a video, try to click the Video button on feed directly
        if video_path and not clicked:
            video_btn = page.get_by_text("Video", exact=True).first
            if await video_btn.count() > 0:
                try:
                    await video_btn.click()
                    logger.info("[LinkedIn] Clicked Video button directly on feed")
                    clicked = True
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.warning(f"[LinkedIn] Direct Video click failed: {e}")
                    
        # Fallback 3: Click the "Start a post" box
        if not clicked:
            start_post = page.get_by_text("Start a post", exact=False).first
            if await start_post.count() > 0:
                try:
                    await start_post.click()
                    logger.info("[LinkedIn] Clicked Start a post box")
                    clicked = True
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.warning(f"[LinkedIn] Start a post box click failed: {e}")
                    
        # Fallback 4: Query selector matching
        if not clicked:
            share_box = await page.query_selector('button.share-box-feed-entry__trigger, button:has-text("Start a post")')
            if share_box:
                await share_box.click()
                logger.info("[LinkedIn] Clicked share_box selector")
                clicked = True
                await page.wait_for_timeout(3000)

        # If we have media to upload
        if media_path:
            # Find the file input or open the file chooser
            file_input = await page.query_selector('input[type="file"]')
            
            # Fallback 2: Click the Media button inside the modal to reveal the file chooser
            if not file_input:
                media_btn = page.get_by_text("Media", exact=True).first
                if await media_btn.count() > 0:
                    try:
                        await media_btn.click()
                        logger.info("[LinkedIn] Clicked Media button inside modal")
                        await page.wait_for_timeout(2000)
                        file_input = await page.query_selector('input[type="file"]')
                    except Exception as e:
                        logger.warning(f"[LinkedIn] Media button click failed: {e}")
                        
            # Fallback 3: Click Add Media button
            if not file_input:
                media_btn_sel = await page.query_selector('button[aria-label="Add media"], button[aria-label="Add a photo"]')
                if media_btn_sel:
                    try:
                        await media_btn_sel.click()
                        await page.wait_for_timeout(2000)
                        file_input = await page.query_selector('input[type="file"]')
                    except Exception as e:
                        logger.warning(f"[LinkedIn] Add media button click failed: {e}")

            if not file_input:
                logger.error("[LinkedIn] Could not find file upload input!")
                await page.screenshot(path=r"C:\Users\absh5\MoneyPrinterTurbo\li_no_input.png")
                await browser.close()
                return {"success": False, "error": "File upload input not found"}

            # ── 4. Upload file ─────────────────────────────
            logger.info(f"[LinkedIn] Uploading media file: {os.path.basename(media_path)}")
            await file_input.set_input_files(media_path)
            await page.wait_for_timeout(10000)
            logger.info("[LinkedIn] Media attached!")
            
            # Click "Next" or "Done" on the media preview if needed
            logger.info("[LinkedIn] Clicking Next/Done button on media preview...")
            clicked_next = False
            for attempt in range(15): # 15 * 5s = 75s max wait for video processing
                next_btn = None
                for selector in [
                    "button:has-text('Next'):visible",
                    "button:has-text('Done'):visible",
                    ".share-box-footer__primary-btn:visible",
                    "button.share-box-footer__primary-btn:visible"
                ]:
                    next_btn = await page.query_selector(selector)
                    if next_btn:
                        break
                if next_btn:
                    try:
                        # Try clicking with a short timeout to check if clickable
                        await next_btn.click(timeout=4000)
                        logger.info("[LinkedIn] Next/Done button clicked successfully!")
                        clicked_next = True
                        break
                    except Exception as click_err:
                        logger.info(f"[LinkedIn] Next/Done click attempt {attempt+1}/15 failed (button might be disabled during upload processing): {click_err}")
                await page.wait_for_timeout(5000)
                
            if not clicked_next:
                raise Exception("Next/Done button could not be clicked (video processing timeout or selector mismatch).")

        try:
            # ── 5. Add Caption / Text ───────────────────────────────────
            editor = await page.query_selector('div[contenteditable="true"][role="textbox"]:visible, .ql-editor:visible')
            if editor:
                await editor.click()
                await page.wait_for_timeout(500)
                await editor.fill(post_text)
                logger.info("[LinkedIn] Caption / Text added!")

            await page.wait_for_timeout(3000)

            # ── 6. Publish ────────────────────────────────────────
            logger.info("[LinkedIn] Waiting for Post button to become enabled...")
            pub_btn = None
            for i in range(30):
                pub_btn = await page.query_selector('.share-actions__primary-action:visible, button.share-actions__primary-action:visible, .share-actions__post-button:visible, .share-actions button:has-text("Post"):visible')
                if pub_btn:
                    is_disabled = await pub_btn.evaluate("el => el.disabled || el.getAttribute('aria-disabled') === 'true'")
                    if not is_disabled:
                        logger.info(f"[LinkedIn] Post button enabled after {i*2}s!")
                        break
                await page.wait_for_timeout(2000)

            if pub_btn:
                # Click it safely
                await pub_btn.click()
                logger.info("[LinkedIn] Clicked Post button")
                await page.wait_for_timeout(15000)
                logger.success("[LinkedIn] Post published successfully!")
                await page.screenshot(path=r"C:\Users\absh5\MoneyPrinterTurbo\li_posted.png")
                return {"success": True, "url": page.url, "method": "playwright"}
            else:
                logger.error("[LinkedIn] Could not find post/publish button")
                await page.screenshot(path=r"C:\Users\absh5\MoneyPrinterTurbo\li_no_publish.png")
                await browser.close()
                return {"success": False, "error": "Post button not found"}
        except Exception as body_err:
            logger.error(f"[LinkedIn-Playwright] Error in post generation flow: {body_err}")
            try:
                await page.screenshot(path=r"C:\Users\absh5\MoneyPrinterTurbo\li_exception_screenshot.png")
                logger.info("Saved exception screenshot to C:\\Users\\absh5\\MoneyPrinterTurbo\\li_exception_screenshot.png")
            except:
                pass
            await browser.close()
            raise body_err


def upload_to_linkedin_playwright(video_path: str = None, image_path: str = None, text: str = None) -> dict:
    """Sync wrapper — call from auto_factory.py or manually"""
    try:
        logger.info("[LinkedIn-Playwright] Starting automated LinkedIn post...")
        result = asyncio.run(_playwright_post(video_path, image_path, text))
        if result and result.get("success"):
            logger.success("[LinkedIn] Posted successfully!")
            return result
        else:
            err = result.get("error","") if result else "unknown error"
            logger.error(f"[LinkedIn] Post failed: {err}")
            return None
    except Exception as e:
        logger.error(f"[LinkedIn-Playwright] Exception: {e}")
        return None


if __name__ == "__main__":
    import glob
    # Find a test video
    videos = glob.glob(os.path.join(project_root, "storage", "tasks", "*", "*.mp4"))
    if not videos:
        print("No test video found")
        sys.exit(1)
    
    test_video = sorted(videos)[-1]
    test_cap   = "Always keep learning and growing! #professional #growth #success #motivation"
    print(f"Test video: {test_video}")
    
    result = upload_to_linkedin_playwright(test_video, test_cap)
    print("Result:", result)
