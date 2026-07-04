import os, sys, json, time, asyncio
from loguru import logger

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IG_COOKIES   = os.path.join(project_root, "instagram_cookies.json")

USERNAME = "shazil5506@gmail.com"
PASSWORD = "mouqeem273red"
PROXY    = "http://172.30.10.10:3128"

def _load(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"[IG] Error loading {path}: {e}")
    return {}

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"[IG] Error saving {path}: {e}")

async def _playwright_post(video_path: str, caption: str) -> dict:
    from playwright.async_api import async_playwright

    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video file not found: {video_path}"}

    # Automatically repair video audio track (resolves corrupt AAC stream errors on Instagram web)
    temp_video_path = None
    import subprocess
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        reencoded_path = video_path.replace(".mp4", "_clean_temp.mp4")
        logger.info("[IG] Re-encoding video audio track to repair stream...")
        subprocess.run([
            ffmpeg_exe, "-y", "-i", video_path,
            "-c:v", "copy", "-c:a", "aac", reencoded_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(reencoded_path):
            temp_video_path = reencoded_path
            video_path = reencoded_path
            logger.info(f"[IG] Repaired video ready for upload: {video_path}")
    except Exception as e:
        logger.warning(f"[IG] Failed to repair/re-encode video: {e}")

    logger.info(f"[IG-Playwright] Uploading: {video_path}")

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

        # Inject saved cookies
        cookies_data = _load(IG_COOKIES)
        if cookies_data.get("cookies"):
            await ctx.add_cookies(cookies_data["cookies"])
            logger.info("[IG] Loaded saved session cookies")

        page = await ctx.new_page()
        # Force fallback to standard file input elements by deleting window.showOpenFilePicker
        await page.add_init_script("window.showOpenFilePicker = undefined;")

        # ── 1. Load Instagram ──────────────────────────────
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=50000)
        await page.wait_for_timeout(4000)

        # ── 2. Login if needed ──────────────────────────────
        async def check_logged_in():
            url = page.url
            if any(x in url for x in ["login", "challenge", "two_factor", "emailsignup", "signup"]):
                return False
            try:
                # Wait up to 5s for either home/create indicator or login form
                await page.wait_for_selector('svg[aria-label="Home"], svg[aria-label="New post"], a[href*="/direct/inbox/"], input[name="username"]', timeout=5000)
            except:
                pass
            logged_in_selectors = [
                'svg[aria-label="Home"]',
                'svg[aria-label="New post"]',
                'a[href*="/direct/inbox/"]',
                'a[href*="/reels/"]',
                'svg[aria-label="Direct"]'
            ]
            for sel in logged_in_selectors:
                if await page.query_selector(sel) is not None:
                    return True
            return False

        logged_in = await check_logged_in()
        if not logged_in:
            logger.info(f"[IG] Not logged in. Navigating to login page...")
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            try:
                # Check for One-Tap login "Continue" button first
                continue_btn = await page.query_selector('button:has-text("Continue"), [role="button"]:has-text("Continue")')
                if continue_btn and await continue_btn.is_visible():
                    logger.info("[IG] One-tap login detected. Clicking 'Continue'...")
                    await continue_btn.click()
                    await page.wait_for_timeout(4000)
                    
                    # Check if password modal popped up
                    password_input = await page.query_selector('input[type="password"], input[name="password"]')
                    if password_input and await password_input.is_visible():
                        logger.info("[IG] Password verification required on modal. Filling password...")
                        await password_input.fill(PASSWORD, timeout=5000)
                        await page.wait_for_timeout(500)
                        login_btn = await page.query_selector('button:has-text("Log in"), button:has-text("Log In")')
                        if login_btn and await login_btn.is_visible():
                            await login_btn.click(timeout=5000)
                        else:
                            await password_input.press("Enter")
                        await page.wait_for_timeout(10000)
                    else:
                        await page.wait_for_timeout(6000)
                        
                    try:
                        await page.screenshot(path="ig_after_continue.png")
                        logger.info("[IG] Saved ig_after_continue.png screenshot")
                    except:
                        pass
                else:
                    # Traditional username/password login
                    user_sel = 'input[name="username"], input[name="email"], input[type="text"]'
                    pass_sel = 'input[name="password"], input[name="pass"], input[type="password"]'
                    await page.wait_for_selector(user_sel, timeout=15000)
                    await page.fill(user_sel, USERNAME, timeout=5000)
                    await page.wait_for_timeout(500)
                    await page.fill(pass_sel, PASSWORD, timeout=500)
                    await page.wait_for_timeout(500)
                    
                    submit_clicked = False
                    submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                    if submit_btn and await submit_btn.is_visible():
                        try:
                            await submit_btn.click(timeout=5000)
                            submit_clicked = True
                        except: pass
                    
                    if not submit_clicked:
                        log_in_div = page.get_by_text("Log in", exact=True).first
                        if await log_in_div.count() > 0 and await log_in_div.is_visible():
                            try:
                                await log_in_div.click(timeout=5000)
                                submit_clicked = True
                            except: pass
                            
                    if not submit_clicked:
                        await page.press(pass_sel, "Enter")
                    await page.wait_for_timeout(8000)
            except Exception as e:
                logger.error(f"[IG] Login form fill error: {e}")
                try:
                    await page.screenshot(path="ig_login_error.png")
                    logger.info("[IG] Saved ig_login_error.png screenshot")
                except:
                    pass

            # Wait for manual 2FA/challenge if it prompts
            url = page.url
            if "challenge" in url or "two_factor" in url or await page.query_selector('input[name="verificationCode"]') is not None:
                logger.warning("[IG] Verification challenge detected! Waiting 30s for manual verification...")
                await page.wait_for_timeout(30000)
            
            # Check login status again
            logged_in = await check_logged_in()

        # Save cookies only if successfully logged in
        if logged_in:
            fresh_cookies = await ctx.cookies()
            _save(IG_COOKIES, {"cookies": fresh_cookies, "saved_at": time.time()})
            logger.info("[IG] Cookies saved successfully")
        else:
            logger.warning("[IG] Not logged in. Skipping cookie save to prevent overwrite.")

        # ── 3. Click Create button ──────────────────────────
        logger.info("[IG] Starting upload flow...")
        create_btn = None
        
        # Dismiss any notifications or save login popups if visible
        popups = [
            'button:has-text("Not Now")',
            'button:has-text("Cancel")',
            'div[role="dialog"] button:has-text("Not Now")'
        ]
        for popup in popups:
            try:
                btn = await page.query_selector(popup)
                if btn and await btn.is_visible():
                    await btn.click()
                    logger.info(f"[IG] Dismissed popup: {popup}")
                    await page.wait_for_timeout(1000)
            except:
                pass

        selectors = [
            'svg[aria-label="New post"]',
            'svg[aria-label="Create"]',
            '[aria-label="New post"]',
            '[aria-label="Create"]',
            'span:has-text("Create")'
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    create_btn = el
                    logger.info(f"[IG] Found Create button using selector: {sel}")
                    break
            except:
                pass
                
        if not create_btn:
            loc = page.get_by_role("link", name="Create").first
            try:
                if await loc.count() > 0 and await loc.is_visible():
                    create_btn = loc
                    logger.info("[IG] Found Create button via role link 'Create'")
            except:
                pass
                
        if not create_btn:
            loc_btn = page.get_by_role("button", name="Create").first
            try:
                if await loc_btn.count() > 0 and await loc_btn.is_visible():
                    create_btn = loc_btn
                    logger.info("[IG] Found Create button via role button 'Create'")
            except:
                pass

        if create_btn:
            await create_btn.click()
            await page.wait_for_timeout(3000)
            
            # Check and click "Post" from submenu if visible
            try:
                post_submenu = None
                
                # Try menuitem role
                loc = page.get_by_role("menuitem", name="Post").first
                if await loc.count() > 0 and await loc.is_visible():
                    post_submenu = loc
                    logger.info("[IG] Found 'Post' submenu item via role menuitem")
                    
                if not post_submenu:
                    # Try exact text Match
                    loc_text = page.get_by_text("Post", exact=True).first
                    if await loc_text.count() > 0 and await loc_text.is_visible():
                        post_submenu = loc_text
                        logger.info("[IG] Found 'Post' submenu item via exact text")
                        
                if not post_submenu:
                    # Try selectors inside popups/menus
                    selectors = [
                        'div[role="menu"] span:has-text("Post")',
                        'div[role="dialog"] span:has-text("Post")',
                        'span:has-text("Post")'
                    ]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            post_submenu = el
                            logger.info(f"[IG] Found 'Post' submenu item via selector: {sel}")
                            break
                            
                if post_submenu:
                    await post_submenu.click()
                    await page.wait_for_timeout(4000)
                else:
                    logger.warning("[IG] 'Post' submenu item not found")
            except Exception as e:
                logger.warning(f"[IG] Submenu Post click error: {e}")
        else:
            logger.error("[IG] Could not find Create/New Post button")
            await page.screenshot(path="ig_no_create_button.png")
            await browser.close()
            return {"success": False, "error": "Create button not found"}

        # ── 4. Upload File ──────────────────────────────────
        file_uploaded = False
        try:
            logger.info("[IG] Attempting to upload video using file chooser...")
            async with page.expect_file_chooser() as fc_info:
                select_btn = await page.query_selector('button:has-text("Select from computer"), [role="button"]:has-text("Select from computer")')
                if select_btn and await select_btn.is_visible():
                    await select_btn.click()
                else:
                    await page.get_by_role("button", name="Select from computer").first.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(video_path)
            logger.info("[IG] File selected via file chooser, waiting for import...")
            await page.wait_for_timeout(6000)
            file_uploaded = True
        except Exception as e:
            logger.error(f"[IG] File chooser upload failed: {e}")
            
        if not file_uploaded:
            try:
                file_input = await page.wait_for_selector('div[role="dialog"] input[type="file"]', state="attached", timeout=5000)
                if file_input:
                    await file_input.set_input_files(video_path)
                    logger.info("[IG] Fallback direct file input selected, waiting...")
                    await page.wait_for_timeout(6000)
                    file_uploaded = True
            except Exception as e2:
                logger.error(f"[IG] Fallback direct file input failed: {e2}")
                
        if not file_uploaded:
            logger.error("[IG] File input not found")
            await page.screenshot(path="ig_upload_error.png")
            await browser.close()
            return {"success": False, "error": "File input not found"}

        # Dismiss "Video posts are now shared as reels" info dialog if it appears
        ok_btn = None
        for sel in ['button:has-text("OK")', '[role="button"]:has-text("OK")', 'span:has-text("OK")']:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    ok_btn = btn
                    break
            except: pass
            
        if ok_btn:
            try:
                await ok_btn.click()
                logger.info("[IG] Dismissed reels info popup")
                await page.wait_for_timeout(2000)
            except: pass

        # Helper function to find and click Next
        async def click_next_step(step_name):
            next_btn = None
            loc = page.get_by_role("button", name="Next").first
            if await loc.count() > 0 and await loc.is_visible():
                next_btn = loc
            if not next_btn:
                loc = page.get_by_text("Next", exact=True).first
                if await loc.count() > 0 and await loc.is_visible():
                    next_btn = loc
            if not next_btn:
                for sel in ['button:has-text("Next")', '[role="button"]:has-text("Next")', 'div:has-text("Next")']:
                    try:
                        btn = await page.query_selector(sel)
                        if btn and await btn.is_visible():
                            next_btn = btn
                            break
                    except: pass
            if next_btn:
                await next_btn.click()
                logger.info(f"[IG] Clicked Next button on {step_name}")
                await page.wait_for_timeout(4000)
                return True
            else:
                logger.warning(f"[IG] Next button not found on {step_name}")
                return False

        # Step 1: Crop page -> Click Next
        await click_next_step("Crop page")

        # Step 2: Cover/Filter page -> Click Next
        await click_next_step("Cover/Filter page")

        # ── 6. Enter Caption & Share ────────────────────────
        caption_input = await page.query_selector('div[aria-label="Write a caption..."], [aria-label="Write a caption"]')
        if caption_input:
            await caption_input.fill(caption)
            await page.wait_for_timeout(2000)
        else:
            logger.warning("[IG] Caption input not found, continuing without caption")

        # Click Share
        share_btn = None
        loc = page.get_by_role("button", name="Share").first
        if await loc.count() > 0 and await loc.is_visible():
            share_btn = loc
        if not share_btn:
            loc = page.get_by_text("Share", exact=True).first
            if await loc.count() > 0 and await loc.is_visible():
                share_btn = loc
        if not share_btn:
            for sel in ['button:has-text("Share")', '[role="button"]:has-text("Share")', 'div:has-text("Share")']:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        share_btn = btn
                        break
                except: pass

        published = False
        if share_btn:
            await share_btn.click()
            logger.info("[IG] Clicked Share button, waiting for upload to complete...")
            await page.wait_for_timeout(30000) # Give it 30s to upload and publish
            published = True

        # Save cookies again
        fresh_cookies = await ctx.cookies()
        _save(IG_COOKIES, {"cookies": fresh_cookies, "saved_at": time.time()})

        await browser.close()

        if published:
            return {"success": True, "method": "playwright"}
        else:
            return {"success": False, "error": "Could not click share/publish button"}

def upload_to_instagram_playwright(video_path: str, caption: str) -> dict:
    try:
        return asyncio.run(_playwright_post(video_path, caption))
    except Exception as e:
        logger.error(f"[IG-Playwright] Run error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Cleanup temporary video file if generated
        reencoded_path = video_path.replace(".mp4", "_clean_temp.mp4")
        if os.path.exists(reencoded_path):
            try:
                os.remove(reencoded_path)
                logger.info(f"[IG] Cleaned up temporary video in wrapper: {reencoded_path}")
            except Exception as clean_err:
                logger.warning(f"[IG] Cleanup failed: {clean_err}")

if __name__ == "__main__":
    # Test script directly if run as main
    import sys
    if len(sys.argv) > 1:
        test_video = sys.argv[1]
        res = upload_to_instagram_playwright(test_video, "Test post from Antigravity automation! #automation #testing")
        print("Result:", res)
    else:
        print("Provide a video path to test.")
