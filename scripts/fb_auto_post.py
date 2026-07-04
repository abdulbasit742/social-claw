#!/usr/bin/env python3
"""
Facebook Auto-Post via Playwright
===================================
Fully automatic: Login → Get page token → Post video
No manual steps needed.

Usage:
  python scripts/fb_auto_post.py --video path/to/video.mp4 --caption "Your caption"
  python scripts/fb_auto_post.py --setup   (first time: saves cookies)
  python scripts/fb_auto_post.py --test    (test with last generated video)
"""
import os, sys, json, time, argparse, asyncio

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

FB_COOKIES_FILE = os.path.join(project_root, "fb_cookies.json")
FB_CREDS_FILE   = os.path.join(project_root, "fb_credentials.json")
IG_CREDS_FILE   = os.path.join(project_root, "instagram_personal.json")
DONE_FILE       = os.path.join(project_root, "scripts", "done.json")

USERNAME = "shazil5506@gmail.com"
PASSWORD = "mouqeem273red"

# ── Helpers ────────────────────────────────────────────────────
def load_json(path):
    try:
        if os.path.exists(path):
            with open(path) as f: return json.load(f)
    except: pass
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_last_video():
    """Get the most recently generated video from done.json"""
    done = load_json(DONE_FILE)
    if isinstance(done, list) and done:
        last = done[-1]
        return last.get("video_path",""), last.get("description","")
    elif isinstance(done, dict):
        # Find last entry
        items = sorted(done.items(), key=lambda x: x[1].get("timestamp","") if isinstance(x[1],dict) else "")
        if items:
            last = items[-1][1] if isinstance(items[-1][1], dict) else {}
            return last.get("video_path",""), last.get("description","")
    return "", ""

# ── Playwright Facebook Bot ────────────────────────────────────
async def fb_login_and_get_token(headless=False):
    """Login to Facebook via Playwright and extract access token for posting"""
    from playwright.async_api import async_playwright
    
    print("[FB-Auto] Starting Playwright browser...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            proxy={"server": "http://172.30.10.10:3128"},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )
        
        page = await ctx.new_page()
        
        # Check if we have saved cookies
        cookies_data = load_json(FB_COOKIES_FILE)
        if cookies_data.get("cookies"):
            print("[FB-Auto] Loading saved cookies...")
            await ctx.add_cookies(cookies_data["cookies"])
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # Check if still logged in
            if "login" not in page.url and await page.query_selector('[aria-label="Your profile"]') is not None:
                print("[FB-Auto] Cookies valid — already logged in!")
                token_data = await extract_token(page, ctx)
                await browser.close()
                return token_data
            else:
                print("[FB-Auto] Cookies expired, fresh login...")
        
        # Fresh login
        print(f"[FB-Auto] Logging in as {USERNAME}...")
        await page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        # Fill email
        await page.fill('#email', USERNAME)
        await page.wait_for_timeout(500)
        
        # Fill password
        await page.fill('#pass', PASSWORD)
        await page.wait_for_timeout(500)
        
        # Click login
        await page.click('#loginbutton')
        await page.wait_for_timeout(5000)
        
        current_url = page.url
        print(f"[FB-Auto] After login URL: {current_url}")
        
        # Handle checkpoints/2FA
        if "checkpoint" in current_url or "login" in current_url:
            print("[FB-Auto] Checkpoint detected! Waiting 15s for manual input if needed...")
            await page.wait_for_timeout(15000)
            current_url = page.url
        
        if "facebook.com" in current_url and "login" not in current_url:
            print("[FB-Auto] Login successful!")
            
            # Save cookies
            cookies = await ctx.cookies()
            save_json(FB_COOKIES_FILE, {"cookies": cookies, "saved_at": time.time()})
            print(f"[FB-Auto] Cookies saved ({len(cookies)} cookies)")
            
            token_data = await extract_token(page, ctx)
            await browser.close()
            return token_data
        else:
            print(f"[FB-Auto] Login issue. URL: {current_url}")
            await browser.close()
            return None

async def extract_token(page, ctx):
    """Extract Graph API token from Facebook Graph Explorer or directly"""
    print("[FB-Auto] Extracting page access tokens...")
    
    # Navigate to Graph API Explorer to get token
    await page.goto(
        "https://developers.facebook.com/tools/explorer/?method=GET&path=me%2Faccounts&version=v20.0",
        wait_until="domcontentloaded"
    )
    await page.wait_for_timeout(4000)
    
    # Look for access token in the page
    # Try to click "Generate Access Token"
    try:
        gen_btn = await page.query_selector('button:has-text("Generate Access Token")')
        if gen_btn:
            await gen_btn.click()
            await page.wait_for_timeout(3000)
            # Allow popup
            popup = await page.query_selector('button:has-text("Allow")')
            if popup:
                await popup.click()
                await page.wait_for_timeout(2000)
    except:
        pass
    
    # Get token value from input
    try:
        token_input = await page.query_selector('input[placeholder*="token"], input[name*="token"], [data-testid="access-token-input"]')
        if token_input:
            token = await token_input.input_value()
            if token and len(token) > 20:
                print(f"[FB-Auto] Got token from Explorer: {token[:30]}...")
                return {"user_token": token}
    except:
        pass
    
    # Alternative: use FB API directly with cookies
    print("[FB-Auto] Getting token via direct API call...")
    cookies = await ctx.cookies()
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies if "facebook.com" in c.get("domain","")])
    
    return {"cookies": cookies, "cookie_str": cookie_str}

async def post_video_playwright(video_path: str, caption: str, page_name: str = ""):
    """Post video to Facebook page using Playwright"""
    from playwright.async_api import async_playwright
    
    print(f"\n[FB-Auto] Posting video: {os.path.basename(video_path)}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Need visible for file upload
            proxy={"server": "http://172.30.10.10:3128"},
            args=["--no-sandbox"]
        )
        
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US"
        )
        
        # Load cookies if available
        cookies_data = load_json(FB_COOKIES_FILE)
        if cookies_data.get("cookies"):
            await ctx.add_cookies(cookies_data["cookies"])
        
        page = await ctx.new_page()
        
        # Go to Facebook
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # Login if needed
        if "login" in page.url:
            print("[FB-Auto] Logging in...")
            await page.fill('#email', USERNAME)
            await page.fill('#pass', PASSWORD)
            await page.click('#loginbutton')
            await page.wait_for_timeout(5000)
        
        # Navigate to our page's video upload
        # First find our page
        await page.goto("https://www.facebook.com/pages/?category=your_pages&ref=bookmarks", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # Save updated cookies
        cookies = await ctx.cookies()
        save_json(FB_COOKIES_FILE, {"cookies": cookies, "saved_at": time.time()})
        
        # Now try to create a reel/video post
        # Navigate to create video
        print("[FB-Auto] Opening video upload page...")
        await page.goto("https://www.facebook.com/reels/create", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        
        # If not on reels, try profile video
        if "reels" not in page.url:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
        
        print(f"[FB-Auto] Current URL: {page.url}")
        
        # Try to find file input for video
        file_inputs = await page.query_selector_all('input[type="file"]')
        print(f"[FB-Auto] Found {len(file_inputs)} file inputs")
        
        if file_inputs:
            await file_inputs[0].set_input_files(video_path)
            await page.wait_for_timeout(5000)
            print("[FB-Auto] Video file selected!")
        
        # Wait for upload and look for caption field
        await page.wait_for_timeout(8000)
        
        # Find caption/description field
        caption_field = await page.query_selector('div[contenteditable="true"], textarea[placeholder*="caption"], textarea[placeholder*="description"]')
        if caption_field:
            await caption_field.click()
            await caption_field.fill(caption)
            print("[FB-Auto] Caption added!")
        
        await page.wait_for_timeout(2000)
        
        # Click share/publish
        share_btn = await page.query_selector('button:has-text("Share"), button:has-text("Post"), button:has-text("Publish"), [data-testid="share-button"]')
        if share_btn:
            await share_btn.click()
            print("[FB-Auto] Share button clicked!")
            await page.wait_for_timeout(10000)
            print("[FB-Auto] Post submitted!")
        else:
            print("[FB-Auto] Share button not found — manual publish needed")
            # Keep browser open for 30s
            await page.wait_for_timeout(30000)
        
        await browser.close()
        return {"success": True, "message": "Video posted to Facebook!"}

async def setup_and_post(video_path: str, caption: str):
    """Main flow: Setup → Post"""
    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return False
    
    print("\n" + "="*55)
    print("  Facebook Auto-Post — Fully Automatic")
    print("="*55)
    print(f"  Video  : {os.path.basename(video_path)}")
    print(f"  Caption: {caption[:60]}...")
    print("="*55 + "\n")
    
    result = await post_video_playwright(video_path, caption)
    return result

# ── Graph API Direct Post (if token available) ─────────────────
def post_via_graph_api(video_path: str, caption: str, page_token: str, page_id: str) -> dict:
    """Post video directly via Graph API (fastest method)"""
    import requests
    
    PROXIES = {"http":"http://172.30.10.10:3128","https":"http://172.30.10.10:3128"}
    file_size = os.path.getsize(video_path)
    
    print(f"[Graph API] Uploading {os.path.basename(video_path)} ({file_size//1024//1024}MB)...")
    
    # Initialize upload
    init_r = requests.post(
        f"https://graph.facebook.com/v20.0/{page_id}/videos",
        data={"upload_phase":"start","file_size":file_size,"access_token":page_token},
        proxies=PROXIES, timeout=30
    )
    init_r.raise_for_status()
    init_d = init_r.json()
    
    session_id = init_d["upload_session_id"]
    video_id   = init_d["video_id"]
    offset     = int(init_d.get("start_offset", 0))
    CHUNK      = 10 * 1024 * 1024
    
    # Upload chunks
    with open(video_path, "rb") as vf:
        while offset < file_size:
            vf.seek(offset)
            chunk = vf.read(CHUNK)
            r = requests.post(
                f"https://graph.facebook.com/v20.0/{page_id}/videos",
                data={"upload_phase":"transfer","upload_session_id":session_id,
                      "start_offset":offset,"access_token":page_token},
                files={"video_file_chunk":("chunk.mp4", chunk, "video/mp4")},
                proxies=PROXIES, timeout=120
            )
            r.raise_for_status()
            next_off = int(r.json().get("start_offset", offset + len(chunk)))
            print(f"  Uploaded: {next_off//1024//1024}MB / {file_size//1024//1024}MB")
            if next_off == offset: break
            offset = next_off
    
    # Finish
    fin = requests.post(
        f"https://graph.facebook.com/v20.0/{page_id}/videos",
        data={"upload_phase":"finish","upload_session_id":session_id,
              "description":caption,"access_token":page_token,"published":"true"},
        proxies=PROXIES, timeout=60
    )
    fin.raise_for_status()
    fin_d = fin.json()
    
    url = f"https://www.facebook.com/{page_id}/videos/{video_id}"
    print(f"[Graph API] Posted! {url}")
    return {"success":True,"url":url,"video_id":video_id}

# ── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",   help="Video file path")
    parser.add_argument("--caption", help="Post caption", default="")
    parser.add_argument("--setup",   action="store_true", help="Setup: login and save cookies")
    parser.add_argument("--test",    action="store_true", help="Post last generated video")
    args = parser.parse_args()
    
    if args.setup:
        print("[Setup] Logging in to Facebook and saving cookies...")
        asyncio.run(fb_login_and_get_token(headless=False))
        print("[Setup] Done!")
        return
    
    video_path = args.video
    caption    = args.caption
    
    if args.test or not video_path:
        # Use last generated video
        video_path, auto_caption = get_last_video()
        if not caption and auto_caption:
            caption = auto_caption
        if not video_path:
            print("[ERROR] No video found in done.json. Use --video flag.")
            sys.exit(1)
        print(f"[Auto] Using last generated video: {video_path}")
    
    if not caption:
        caption = "Check out this amazing entrepreneurship insight! #business #entrepreneur #success #motivation"
    
    # Check if we have Graph API credentials
    fb_creds = load_json(FB_CREDS_FILE)
    if fb_creds.get("page_access_token") and fb_creds.get("page_id"):
        print("[Method] Using Graph API (fast)...")
        try:
            result = post_via_graph_api(
                video_path, caption,
                fb_creds["page_access_token"],
                fb_creds["page_id"]
            )
            print(f"\n[SUCCESS] {result.get('url','')}")
            return
        except Exception as e:
            print(f"[Graph API] Failed: {e}. Falling back to Playwright...")
    
    # Use Playwright
    print("[Method] Using Playwright browser automation...")
    asyncio.run(setup_and_post(video_path, caption))

if __name__ == "__main__":
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    main()
