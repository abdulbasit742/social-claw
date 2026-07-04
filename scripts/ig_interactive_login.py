import asyncio, json, os, time, sys
from playwright.async_api import async_playwright

USERNAME = "shazil5506@gmail.com"
PASSWORD = "mouqeem273red"
PROXY    = "http://172.30.10.10:3128"

async def wait_for_home(page, timeout_sec=300):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        url = page.url
        if 'instagram.com' in url and not any(x in url for x in ['login', 'challenge', 'two_factor', 'emailsignup', 'signup']):
            return True
        remaining = int(deadline - time.time())
        print(f'  [WAIT] On: {url[:80]}  ({remaining}s remaining...)')
        await page.wait_for_timeout(4000)
    return False

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
        
        # Load existing cookies if any
        if os.path.exists('instagram_cookies.json'):
            with open('instagram_cookies.json') as f:
                try:
                    d = json.load(f)
                    if d.get('cookies'):
                        await ctx.add_cookies(d['cookies'])
                        print('[IG] Loaded existing cookies')
                except: pass
        
        print('[IG] Loading Instagram login page...')
        await page.goto('https://www.instagram.com/accounts/login/', timeout=60000, wait_until='domcontentloaded')
        
        user_sel = 'input[name="username"], input[name="email"], input[type="text"]'
        pass_sel = 'input[name="password"], input[name="pass"], input[type="password"]'
        
        try:
            print('[IG] Waiting for username field...')
            await page.wait_for_selector(user_sel, timeout=20000)
            print('[IG] Entering username/password...')
            await page.fill(user_sel, USERNAME)
            await page.wait_for_timeout(1000)
            await page.fill(pass_sel, PASSWORD)
            await page.wait_for_timeout(1000)
            
            # Click or press Enter to submit
            submit_clicked = False
            submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
            if submit_btn and await submit_btn.is_visible():
                try:
                    await submit_btn.click(timeout=5000)
                    submit_clicked = True
                    print('[IG] Clicked type="submit" element.')
                except: pass
                
            if not submit_clicked:
                log_in_div = page.get_by_text("Log in", exact=True).first
                if await log_in_div.count() > 0 and await log_in_div.is_visible():
                    try:
                        await log_in_div.click(timeout=5000)
                        submit_clicked = True
                        print('[IG] Clicked visible "Log in" text div.')
                    except: pass
                    
            if not submit_clicked:
                print('[IG] Fallback: Pressing Enter key on password field.')
                await page.press(pass_sel, "Enter")
                
            await page.wait_for_timeout(8000)
        except Exception as e:
            print('[IG] Login fields not found or input error:', e)
            
        print('[IG] Current URL:', page.url)
        print('[IG] Waiting for 2FA / Checkpoint / Manual Verification (5 minutes limit)...')
        
        logged_in = await wait_for_home(page, timeout_sec=300)
        if logged_in:
            print('[IG] SUCCESSFUL LOGIN!')
            cookies = await ctx.cookies()
            with open('instagram_cookies.json', 'w') as f:
                json.dump({'cookies': cookies, 'saved_at': time.time()}, f)
            print('[IG] Saved fresh cookies to instagram_cookies.json!')
        else:
            print('[IG] FAILED or Timeout.')
            await page.screenshot(path='ig_failed_login.png')
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
