import asyncio, json, os, time, sys
from playwright.async_api import async_playwright

VIDEO = r'C:\Users\absh5\MoneyPrinterTurbo\storage\tasks\522dabb5-f14e-4f73-a64c-7ea25644a72f\final-1.mp4'
USERNAME = 'shazil5506@gmail.com'
PASSWORD = 'mouqeem273red'
PROXY = 'http://172.30.10.10:3128'

async def wait_for_home(page, timeout_sec=300):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        url = page.url
        if 'facebook.com' in url and not any(x in url for x in ['login','checkpoint','two_step','captcha','recover']):
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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width':1366,'height':768}
        )
        page = await ctx.new_page()
        
        # Load existing cookies if any
        if os.path.exists('fb_cookies.json'):
            with open('fb_cookies.json') as f:
                try:
                    d = json.load(f)
                    if d.get('cookies'):
                        await ctx.add_cookies(d['cookies'])
                        print('[FB] Loaded existing cookies')
                except: pass
        
        print('[FB] Loading Facebook login page...')
        await page.goto('https://www.facebook.com/login', timeout=45000, wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        
        # Fill credentials if login form is detected
        email_sel = 'input[name="email"], input[type="email"], #email'
        pass_sel  = 'input[name="pass"], input[type="password"], #pass'
        
        if 'login' in page.url or await page.query_selector(email_sel) is not None:
            print('[FB] Entering email/password...')
            await page.fill(email_sel, USERNAME)
            await page.wait_for_timeout(600)
            await page.fill(pass_sel, PASSWORD)
            await page.wait_for_timeout(600)
            await page.press(pass_sel, 'Enter')
            await page.wait_for_timeout(5000)
            
        print('[FB] Current URL:', page.url)
        print('[FB] Waiting for 2FA / Manual Verification (5 minutes limit)...')
        
        logged_in = await wait_for_home(page, timeout_sec=300)
        if logged_in:
            print('[FB] SUCCESSFUL LOGIN!')
            cookies = await ctx.cookies()
            with open('fb_cookies.json', 'w') as f:
                json.dump({'cookies': cookies, 'saved_at': time.time()}, f)
            print('[FB] Saved fresh cookies to fb_cookies.json!')
        else:
            print('[FB] FAILED or Timeout.')
            await page.screenshot(path='fb_failed_login.png')
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
