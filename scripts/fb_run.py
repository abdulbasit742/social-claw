import asyncio, json, os, time, sys
from playwright.async_api import async_playwright

VIDEO   = r'C:\Users\absh5\MoneyPrinterTurbo\storage\tasks\522dabb5-f14e-4f73-a64c-7ea25644a72f\final-1.mp4'
CAPTION = 'Entrepreneurs: Execution beats perfection every time! Start before you are ready. #entrepreneurship #business #success #motivation #startup'
USERNAME = 'shazil5506@gmail.com'
PASSWORD = 'mouqeem273red'
PROXY    = 'http://172.30.10.10:3128'
COOKIES_FILE = r'C:\Users\absh5\MoneyPrinterTurbo\fb_cookies.json'

def load_cookies():
    try:
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE) as f:
                d = json.load(f)
                return d.get('cookies', [])
    except: pass
    return []

def save_cookies(cookies):
    with open(COOKIES_FILE, 'w') as f:
        json.dump({'cookies': cookies, 'saved_at': time.time()}, f)
    print(f'[FB] {len(cookies)} cookies saved')

async def wait_for_home(page, timeout_sec=180):
    """Wait until FB home/feed is reached (past login + CAPTCHA + 2FA)"""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        url = page.url
        if 'facebook.com' in url and not any(x in url for x in ['login','checkpoint','two_step','captcha','recover']):
            return True
        remaining = int(deadline - time.time())
        print(f'  [WAIT] On: {url[:80]}  ({remaining}s remaining...)')
        await page.wait_for_timeout(3000)
    return False

async def upload_video(page, video_path, caption):
    """Navigate to reels creator and upload video"""
    print('\n[FB] === Starting Video Upload ===')

    # Try reels/create first
    await page.goto('https://www.facebook.com/reels/create', timeout=30000, wait_until='domcontentloaded')
    await page.wait_for_timeout(5000)
    print('[FB] Reels URL:', page.url)

    # If redirected to login, try profile video upload
    if 'login' in page.url:
        print('[FB] Reels page requires extra auth — trying /video/upload ...')
        await page.goto('https://www.facebook.com/video/upload', timeout=30000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)

    await page.screenshot(path=r'C:\Users\absh5\MoneyPrinterTurbo\fb_upload_page.png')

    # Find file input
    file_input = None
    for sel in ['input[type="file"][accept*="video"]', 'input[type="file"]']:
        inputs = await page.query_selector_all(sel)
        if inputs:
            file_input = inputs[0]
            print(f'[FB] Found file input with selector: {sel}')
            break

    if not file_input:
        # Try clicking create post on home feed
        print('[FB] No file input — trying home feed create post...')
        await page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Look for "Photo/video" or "Reels" button
        for btn_text in ['Reel', 'Photo/video', 'Video']:
            try:
                btn = page.get_by_text(btn_text, exact=False)
                if await btn.count() > 0:
                    await btn.first.click()
                    await page.wait_for_timeout(3000)
                    print(f'[FB] Clicked: {btn_text}')
                    break
            except: pass

        for sel in ['input[type="file"]']:
            inputs = await page.query_selector_all(sel)
            if inputs:
                file_input = inputs[0]
                break

    if not file_input:
        print('[FB] ERROR: Could not find file upload input')
        await page.screenshot(path=r'C:\Users\absh5\MoneyPrinterTurbo\fb_no_input.png')
        return False

    # Upload video
    print(f'[FB] Attaching video: {os.path.basename(video_path)}')
    await file_input.set_input_files(video_path)
    await page.wait_for_timeout(15000)  # Wait for upload progress
    await page.screenshot(path=r'C:\Users\absh5\MoneyPrinterTurbo\fb_after_attach.png')
    print('[FB] Video attached! Waiting for processing...')

    # Add caption
    for cap_sel in [
        'div[contenteditable="true"][aria-label*="caption"]',
        'div[contenteditable="true"][aria-label*="description"]',
        'div[contenteditable="true"]',
        'textarea[placeholder*="caption"]',
        'textarea',
    ]:
        cap = await page.query_selector(cap_sel)
        if cap:
            try:
                await cap.click()
                await page.wait_for_timeout(500)
                await page.keyboard.type(caption)
                print(f'[FB] Caption typed using: {cap_sel}')
                break
            except: pass

    await page.wait_for_timeout(2000)
    await page.screenshot(path=r'C:\Users\absh5\MoneyPrinterTurbo\fb_with_caption.png')

    # Publish
    for btn_name in ['Share now', 'Share', 'Post', 'Publish', 'Next']:
        try:
            btn = page.get_by_role('button', name=btn_name)
            if await btn.count() > 0 and await btn.first.is_enabled():
                await btn.first.click()
                print(f'[FB] Clicked publish: {btn_name}')
                await page.wait_for_timeout(20000)
                await page.screenshot(path=r'C:\Users\absh5\MoneyPrinterTurbo\fb_posted.png')
                print('[FB] POST SUBMITTED!')
                print('[FB] Final URL:', page.url)
                return True
        except: pass

    # Try any enabled submit button
    try:
        btns = await page.query_selector_all('button[type="submit"], button.share, div[role="button"]')
        for btn in btns:
            text = await btn.inner_text()
            if any(w in text.lower() for w in ['share','post','publish','next']):
                if await btn.is_enabled():
                    await btn.click()
                    print(f'[FB] Clicked button: {text}')
                    await page.wait_for_timeout(20000)
                    return True
    except: pass

    print('[FB] Could not find publish button')
    await page.screenshot(path=r'C:\Users\absh5\MoneyPrinterTurbo\fb_no_publish_btn.png')
    return False


async def main():
    print('='*55)
    print('  Facebook Auto-Post — Playwright')
    print('='*55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy={'server': PROXY},
            args=['--no-sandbox','--start-maximized',
                  '--disable-blink-features=AutomationControlled',
                  '--disable-infobars']
        )
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width':1366,'height':768}
        )

        # Load saved cookies
        saved = load_cookies()
        if len(saved) > 10:
            print(f'[FB] Loading {len(saved)} saved cookies...')
            await ctx.add_cookies(saved)

        page = await ctx.new_page()

        # Check if already logged in
        print('[FB] Checking session...')
        await page.goto('https://www.facebook.com/', timeout=40000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        if 'login' in page.url or await page.query_selector('input[name="email"]') is not None:
            print(f'[FB] Logging in as {USERNAME}...')
            await page.goto('https://www.facebook.com/login', timeout=30000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            await page.fill('input[name="email"]', USERNAME)
            await page.wait_for_timeout(600)
            await page.fill('input[name="pass"]', PASSWORD)
            await page.wait_for_timeout(600)
            await page.press('input[name="pass"]', 'Enter')
            await page.wait_for_timeout(5000)

        # Wait for home (handles CAPTCHA / 2FA manually by user)
        url = page.url
        print('[FB] Current URL:', url[:80])

        needs_manual = any(x in url for x in ['two_step','captcha','checkpoint','login','recover'])
        if needs_manual:
            print()
            print('*'*55)
            print('  ACTION NEEDED IN BROWSER WINDOW:')
            print('  Complete CAPTCHA or 2FA verification')
            print('  You have 3 minutes...')
            print('*'*55)

        logged_in = await wait_for_home(page, timeout_sec=180)

        if logged_in:
            print('[FB] Successfully on Facebook home!')
            cookies = await ctx.cookies()
            save_cookies(cookies)

            # Upload video
            success = await upload_video(page, VIDEO, CAPTION)
            if success:
                print()
                print('='*55)
                print('  Facebook POST SUCCESSFUL!')
                print(f'  URL: {page.url}')
                print('='*55)
            else:
                print('[FB] Upload failed - check screenshots in project folder')
        else:
            print('[FB] Timeout - could not reach Facebook home')

        print('[FB] Keeping browser open for 10s...')
        await page.wait_for_timeout(10000)
        await browser.close()

asyncio.run(main())
