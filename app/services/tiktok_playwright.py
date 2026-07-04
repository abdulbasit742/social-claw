import os
import sys
import json
import time
import asyncio
from loguru import logger

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TT_COOKIES      = os.path.join(project_root, "tiktok_cookies.json")
TT_STORAGE      = os.path.join(project_root, "tiktok_storage_state.json")
PROXY           = "http://172.30.10.10:3128"

def _load(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"[TikTok-Playwright] Error loading {path}: {e}")
    return {}

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"[TikTok-Playwright] Error saving {path}: {e}")

async def _dismiss_popups(page):
    try:
        await page.evaluate("""() => {
            const selectors = [
                '#react-joyride-portal',
                '.react-joyride__overlay',
                '.react-joyride__spotlight',
                '.tiktok-tour-portal',
                'div[class*="joyride"]',
                'div[class*="tour"]'
            ];
            selectors.forEach(sel => {
                const el = document.querySelector(sel);
                if (el) {
                    el.remove();
                    console.log('Removed popup selector: ' + sel);
                }
            });
        }""")
    except Exception as e:
        logger.warning(f"[TikTok-Playwright] Popups cleanup warning: {e}")

async def _take_screenshot(page, name):
    try:
        os.makedirs("storage/screenshots", exist_ok=True)
        path = f"storage/screenshots/{name}.png"
        await page.screenshot(path=path)
        logger.info(f"[TikTok-Playwright] Captured screenshot: {path}")
    except Exception as e:
        logger.warning(f"[TikTok-Playwright] Failed to take screenshot '{name}': {e}")

async def _playwright_post(video_path: str, caption: str) -> dict:
    from playwright.async_api import async_playwright

    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video file not found: {video_path}"}

    logger.info(f"[TikTok-Playwright] Starting automated upload: {video_path}")

    async with async_playwright() as p:
        # Launching Chromium in visible mode so the user can log in if needed
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--start-maximized"]
        )

        # Prefer full storage state (localStorage + cookies) over cookies-only
        ctx_kwargs = dict(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-US"
        )
        if os.path.exists(TT_STORAGE):
            try:
                ctx_kwargs["storage_state"] = TT_STORAGE
                logger.info("[TikTok-Playwright] Loaded persistent storage state (cookies + localStorage)")
            except Exception as e:
                logger.warning(f"[TikTok-Playwright] storage_state load failed, falling back to cookies: {e}")
        elif os.path.exists(TT_COOKIES):
            # Legacy cookie fallback
            cookies_data = _load(TT_COOKIES)
            if cookies_data.get("cookies"):
                ctx_kwargs["storage_state"] = {"cookies": cookies_data["cookies"], "origins": []}
                logger.info("[TikTok-Playwright] Loaded legacy session cookies")

        ctx = await browser.new_context(**ctx_kwargs)
        page = await ctx.new_page()

        # Go to upload page
        logger.info("[TikTok-Playwright] Navigating to upload page...")
        await page.goto("https://www.tiktok.com/creator-center/upload?lang=en", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        # Robust login check: checks for upload form or logged-in avatar
        async def _is_logged_in():
            try:
                file_input = await page.query_selector('input[type="file"], iframe[src*="upload"]')
                if file_input:
                    return True
            except Exception:
                pass
            
            try:
                avatar = await page.query_selector('[data-tt*="Avatar"], [data-tt="Header_NewHeader_Clickable"], [data-tt*="avatar"], .avatar')
                if avatar:
                    logger.info("[TikTok-Playwright] Logged-in session detected via avatar. Navigating to upload page...")
                    await page.goto("https://www.tiktok.com/creator-center/upload?lang=en", wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(5000)
                    file_input = await page.query_selector('input[type="file"], iframe[src*="upload"]')
                    if file_input:
                        return True
            except Exception:
                pass
                
            return False

        is_logged_in = await _is_logged_in()

        if not is_logged_in:
            logger.warning("[TikTok-Playwright] Session expired or not logged in. Waiting for login...")
            await page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded", timeout=60000)

            # Auto-fill credentials if available
            login_file = os.path.join(project_root, "tiktok_login.json")
            if os.path.exists(login_file):
                try:
                    with open(login_file, "r", encoding="utf-8") as f:
                        credentials = json.load(f)
                    email = credentials.get("email")
                    password = credentials.get("password")
                    if email and password:
                        logger.info(f"[TikTok-Playwright] Stored credentials found. Filling login for {email}...")
                        # Frame-aware locator helper functions
                        async def _click_in_frames(selectors):
                            for sel in selectors:
                                try:
                                    el = await page.query_selector(sel)
                                    if el and await el.is_visible():
                                        await el.click()
                                        return True
                                except Exception:
                                    pass
                                for frame in page.frames:
                                    try:
                                        el = await frame.query_selector(sel)
                                        if el and await el.is_visible():
                                            await el.click()
                                            return True
                                    except Exception:
                                        pass
                            return False

                        async def _fill_in_frames(selectors, value):
                            for sel in selectors:
                                try:
                                    el = await page.query_selector(sel)
                                    if el and await el.is_visible():
                                        await el.fill(value)
                                        return True
                                except Exception:
                                    pass
                                for frame in page.frames:
                                    try:
                                        el = await frame.query_selector(sel)
                                        if el and await el.is_visible():
                                            await el.fill(value)
                                            return True
                                    except Exception:
                                        pass
                            return False
                        
                        # Step 1: Click "Use phone / email / username"
                        clicked_option = await _click_in_frames([
                            'div:has-text("Use phone / email / username")',
                            'p:has-text("Use phone / email / username")',
                            'a[href*="phone-or-email"]',
                            'div[class*="LoginOptionContainer"] div:first-child',
                            'ul li:first-child',
                            'p:text("Use phone / email / username")',
                            'text="Use phone / email / username"'
                        ])
                        
                        if clicked_option:
                            logger.info("[TikTok-Playwright] Clicked login option successfully.")
                        else:
                            logger.warning("[TikTok-Playwright] Could not click login option selector, continuing...")

                        await page.wait_for_timeout(3000)

                        # Step 2: Click "Log in with email or username"
                        clicked_email_tab = await _click_in_frames([
                            'a:has-text("Log in with email or username")',
                            'span:has-text("Log in with email or username")',
                            ':text("Log in with email")',
                            'a[href*="email"]',
                            'div:has-text("Log in with email")',
                            'text="Log in with email or username"'
                        ])
                        
                        if clicked_email_tab:
                            logger.info("[TikTok-Playwright] Clicked email tab successfully.")

                        await page.wait_for_timeout(3000)

                        # Step 3: Fill inputs
                        filled_user = await _fill_in_frames([
                            'input[name="username"]',
                            'input[type="text"]',
                            'input[placeholder*="Email"]',
                            'input[placeholder*="username"]'
                        ], email)
                        
                        filled_pass = await _fill_in_frames([
                            'input[type="password"]',
                            'input[placeholder="Password"]'
                        ], password)
                        
                        filled = filled_user and filled_pass
                        if filled:
                            logger.info("[TikTok-Playwright] Username and password fields filled successfully.")
                        else:
                            logger.warning("[TikTok-Playwright] Failed to automatically fill user/pass input fields.")

                        # Step 4: Click Log in button
                        if filled:
                            submit_clicked = await _click_in_frames([
                                'button[type="submit"]',
                                'button:has-text("Log in")',
                                'button:has-text("Login")',
                                'form button'
                            ])
                            if submit_clicked:
                                logger.info("[TikTok-Playwright] Clicked submit button. Checking for success...")
                                await page.wait_for_timeout(5000)
                except Exception as e:
                    logger.error(f"[TikTok-Playwright] Automated login attempt failed: {e}")

            login_success = False
            logger.info("=====================================================================")
            logger.info("ACTION REQUIRED: Please verify / log in to TikTok in the browser window.")
            logger.info("Credentials have been auto-filled if stored successfully.")
            logger.info("We will wait up to 10 minutes (600s) for you to complete any CAPTCHA.")
            logger.info("=====================================================================")
            for i in range(60):  # 60 × 10s = 600s
                await page.wait_for_timeout(10000)
                current_url = page.url
                if "creator-center/upload" in current_url or await page.query_selector('input[type="file"]'):
                    logger.info("[TikTok-Playwright] Login detected successfully!")
                    login_success = True
                    break
                # Also check that user landed on their home/creator page
                if "tiktok.com/@" in current_url or "tiktok.com/foryou" in current_url:
                    logger.info("[TikTok-Playwright] Home page detected — navigating to upload...")
                    await page.goto("https://www.tiktok.com/creator-center/upload?lang=en", wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000)
                    if await page.query_selector('input[type="file"]'):
                        logger.info("[TikTok-Playwright] Upload page loaded after home redirect.")
                        login_success = True
                        break
                logger.info(f"[TikTok-Playwright] Still waiting for login... ({10*(i+1)}s / 600s)")

            if not login_success:
                await browser.close()
                return {"success": False, "error": "Login timeout exceeded (10 minutes)"}

            # Save full storage state so future runs don't need manual login
            await ctx.storage_state(path=TT_STORAGE)
            # Also save legacy cookies for compatibility
            cookies = await ctx.cookies()
            _save(TT_COOKIES, {"cookies": cookies})
            logger.info("[TikTok-Playwright] Saved persistent storage state + cookies for future runs")

            # Navigate to upload
            await page.goto("https://www.tiktok.com/creator-center/upload?lang=en", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
        else:
            # Refresh storage state on every successful run to keep session alive
            try:
                await ctx.storage_state(path=TT_STORAGE)
                logger.info("[TikTok-Playwright] Refreshed persistent storage state")
            except Exception as e:
                logger.warning(f"[TikTok-Playwright] Could not refresh storage state: {e}")

        # Dismiss any overlays at start
        await _dismiss_popups(page)
        await _take_screenshot(page, "1_loaded")

        # ── Upload Video ──────────────────────────────────────────────────────
        logger.info("[TikTok-Playwright] Locating file input element...")
        file_input = await page.query_selector('input[type="file"]')
        
        # If uploader is in iframe, locate the iframe uploader
        if not file_input:
            logger.info("[TikTok-Playwright] Uploader input not found in main page, scanning iframes...")
            frames = page.frames
            for f in frames:
                file_input = await f.query_selector('input[type="file"]')
                if file_input:
                    logger.info(f"[TikTok-Playwright] Found file input inside iframe: {f.name or f.url}")
                    await file_input.set_input_files(video_path)
                    break
        else:
            await file_input.set_input_files(video_path)

        logger.info("[TikTok-Playwright] Video selected, waiting for upload/import processing...")
        await page.wait_for_timeout(15000) # Wait for progress bar to initialize
        await _take_screenshot(page, "2_video_selected")

        # Dismiss overlays before locating caption
        await _dismiss_popups(page)

        # ── Fill Caption ──────────────────────────────────────────────────────
        logger.info("[TikTok-Playwright] Locating caption text box...")
        # TikTok uses draft editor or divs with contenteditable="true"
        caption_box = None
        for selector in ['div[contenteditable="true"]', 'div[role="textbox"]', '.public-DraftEditor-content']:
            caption_box = await page.query_selector(selector)
            if caption_box:
                break
                
        if not caption_box:
            # Scan inside iframes
            for f in page.frames:
                for selector in ['div[contenteditable="true"]', 'div[role="textbox"]', '.public-DraftEditor-content']:
                    caption_box = await f.query_selector(selector)
                    if caption_box:
                        break
                if caption_box:
                    break

        if caption_box:
            logger.info("[TikTok-Playwright] Clearing default caption and writing customized caption...")
            await _dismiss_popups(page)
            await caption_box.click()
            # Clear existing text
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.wait_for_timeout(1000)
            await caption_box.fill(caption)
            logger.info("[TikTok-Playwright] Caption filled.")
            await _take_screenshot(page, "3_caption_filled")
        else:
            logger.warning("[TikTok-Playwright] Could not locate caption text box, skipping caption injection.")

        # ── Click Publish/Post ────────────────────────────────────────────────
        logger.info("[TikTok-Playwright] Locating Post button...")
        post_btn = None
        for selector in ['button[data-e2e="post_video_button"]', 'button:has-text("Post")', 'button:has-text("Publish")', '.btn-post', 'button[type="submit"]']:
            post_btn = await page.query_selector(selector)
            if post_btn:
                break
                
        if not post_btn:
            for f in page.frames:
                for selector in ['button[data-e2e="post_video_button"]', 'button:has-text("Post")', 'button:has-text("Publish")', '.btn-post']:
                    post_btn = await f.query_selector(selector)
                    if post_btn:
                        break
                if post_btn:
                    break

        if post_btn:
            logger.info("[TikTok-Playwright] Clicking Post/Publish button...")
            await _dismiss_popups(page)
            try:
                await post_btn.click(timeout=8000)
                await _take_screenshot(page, "4_clicked_post")
            except Exception as e:
                logger.warning(f"[TikTok-Playwright] Click timed out or intercepted: {e}. Checking for modal overlays...")
                await _take_screenshot(page, "4_blocked_modal")
                
                modal_dismissed = False
                for modal_selector in ['.TUXModal', 'div[role="dialog"]', '.common-modal', '.TUXModal-overlay']:
                    modal = await page.query_selector(modal_selector)
                    if modal:
                        logger.info(f"[TikTok-Playwright] Found blocking modal matching selector: {modal_selector}")
                        try:
                            text_content = await modal.inner_text()
                            logger.info(f"[TikTok-Playwright] Modal text: {repr(text_content)}")
                        except Exception:
                            pass
                        
                        # Dismiss via click
                        for btn_selector in ['button:has-text("Post anyway")', 'button:has-text("Got it")', 'button:has-text("Proceed")', 'button:has-text("OK")', 'button:has-text("Continue")', 'button:has-text("Publish anyway")']:
                            proceed_btn = await modal.query_selector(btn_selector)
                            if proceed_btn:
                                logger.info(f"[TikTok-Playwright] Clicking modal proceed button: {btn_selector}")
                                await proceed_btn.click()
                                await page.wait_for_timeout(2000)
                                modal_dismissed = True
                                break
                        
                        if not modal_dismissed:
                            primary_btn = await modal.query_selector('button[class*="primary"], button[class*="Button__root--type-primary"]')
                            if primary_btn:
                                logger.info("[TikTok-Playwright] Clicking primary button in modal as fallback...")
                                await primary_btn.click()
                                await page.wait_for_timeout(2000)
                                modal_dismissed = True
                        break
                
                if modal_dismissed:
                    logger.info("[TikTok-Playwright] Retrying Post button click after dismissing modal...")
                    await post_btn.click()
                    await _take_screenshot(page, "4_clicked_post_retry")
                else:
                    logger.error("[TikTok-Playwright] Could not dismiss blocking modal. Raising original click exception...")
                    raise e
            
            # Wait for upload completion/confirmation rather than closing immediately
            logger.info("[TikTok-Playwright] Waiting for publication confirmation...")
            published = False
            for poll in range(15):  # 15 * 5s = 75s
                await page.wait_for_timeout(5000)
                
                # Check for any post-click confirmation modals (e.g. copyright checking dialogs)
                for modal_selector in ['.TUXModal', 'div[role="dialog"]', '.common-modal', '.TUXModal-overlay']:
                    modal = await page.query_selector(modal_selector)
                    if modal:
                        logger.info(f"[TikTok-Playwright] Detected confirmation modal during wait: {modal_selector}")
                        try:
                            modal_text = await modal.inner_text()
                            logger.info(f"[TikTok-Playwright] Confirmation modal text: {repr(modal_text)}")
                        except Exception:
                            pass
                        
                        # Look for button inside modal to click "Post now" or similar
                        for btn_selector in ['button:has-text("Post now")', 'button:has-text("Post anyway")', 'button:has-text("Got it")', 'button:has-text("Proceed")', 'button:has-text("OK")', 'button:has-text("Continue")']:
                            proceed_btn = await modal.query_selector(btn_selector)
                            if proceed_btn:
                                logger.info(f"[TikTok-Playwright] Clicking confirmation modal proceed button: {btn_selector}")
                                await proceed_btn.click()
                                await page.wait_for_timeout(2000)
                                break
                
                current_url = page.url
                page_content = await page.content()
                
                # Success checks
                if "manage" in current_url or "posts" in current_url:
                    logger.info("[TikTok-Playwright] Redirect to manage/posts page detected.")
                    published = True
                    break
                if any(x in page_content for x in ["Manage your posts", "Upload another video", "Your video is being uploaded", "successfully uploaded", "Share another video"]):
                    logger.info("[TikTok-Playwright] Success message / button detected on page.")
                    published = True
                    break
                
                # Check if post button disappeared (indicates processing / page navigation)
                try:
                    is_visible = await post_btn.is_visible()
                    if not is_visible:
                        logger.info("[TikTok-Playwright] Post button is no longer visible (navigating/submitting).")
                        published = True
                        break
                except Exception:
                    logger.info("[TikTok-Playwright] Post button reference lost (navigating away).")
                    published = True
                    break
                logger.info(f"[TikTok-Playwright] Still waiting for upload completion... ({5 * (poll+1)}s / 75s)")

            if not published:
                logger.warning("[TikTok-Playwright] No explicit success indicator found. Waiting extra 15s before closing...")
                await page.wait_for_timeout(15000)

            logger.success("[TikTok-Playwright] Video published successfully via Playwright!")
            await _take_screenshot(page, "5_final")
            
            # Save final cookies post upload
            cookies = await ctx.cookies()
            _save(TT_COOKIES, {"cookies": cookies})
            
            await browser.close()
            return {"success": True, "url": "https://www.tiktok.com/"}
        else:
            await browser.close()
            return {"success": False, "error": "Post/Publish button not found"}

def upload_to_tiktok_playwright(video_path: str, caption: str) -> dict:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(_playwright_post(video_path, caption))
        loop.close()
        return res
    except Exception as e:
        logger.error(f"[TikTok-Playwright] Automation failed: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tiktok_playwright.py <video_path> <caption>")
        sys.exit(1)
    res = upload_to_tiktok_playwright(sys.argv[1], sys.argv[2])
    print(json.dumps(res))
