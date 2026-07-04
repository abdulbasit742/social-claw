import os
import re
import json
import time
import requests
from datetime import datetime
from loguru import logger

# Paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DONE_PATH = os.path.join(REPO_ROOT, "scripts", "done.json")
ANALYTICS_LOGS_DIR = os.path.join(REPO_ROOT, "logs")

# Proxy
PROXY_URL = "http://172.30.10.10:3128"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

def extract_youtube_video_id(url: str) -> str:
    if not url:
        return None
    match = re.search(r"(?:v=|\/shorts\/|embed\/|youtu\.be\/)([^&\s?#]+)", url)
    return match.group(1) if match else None

def fetch_youtube_stats(video_url: str) -> dict:
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        return {}
        
    try:
        from app.services.youtube_upload import get_authenticated_service
        youtube = get_authenticated_service()
        res = youtube.videos().list(id=video_id, part="statistics").execute()
        if res.get("items"):
            stats = res["items"][0]["statistics"]
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0))
            }
    except Exception as e:
        logger.warning(f"[Analytics] Failed to fetch YouTube stats for {video_id}: {e}")
    return {}

def fetch_meta_post_stats(post_url: str, platform: str) -> dict:
    """Fetch Facebook or Instagram stats via Graph API if configured"""
    if not post_url or "skipped" in post_url or "local-only" in post_url:
        return {}
        
    try:
        from app.services.meta_upload import load_meta_credentials
        creds = load_meta_credentials()
        if not creds:
            return {}
            
        token = creds.get("access_token")
        if not token:
            return {}
            
        # Parse post ID from URL
        # e.g., Facebook reel: facebook.com/reel/1523403885646387/ -> 1523403885646387
        match = re.search(r"/(?:reel|posts|videos|p)/([a-zA-Z0-9_]+)", post_url)
        if not match:
            return {}
        media_id = match.group(1)
        
        # Meta Graph API endpoint
        url = f"https://graph.facebook.com/v20.0/{media_id}"
        if platform == "instagram":
            params = {
                "fields": "like_count,comments_count",
                "access_token": token
            }
        else: # Facebook
            params = {
                "fields": "reactions.summary(total_count),comments.summary(total_count)",
                "access_token": token
            }
            
        res = requests.get(url, params=params, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if platform == "instagram":
                return {
                    "likes": int(data.get("like_count", 0)),
                    "comments": int(data.get("comments_count", 0)),
                    "views": 0 # reach requires specific insights endpoints
                }
            else: # Facebook
                reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
                comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
                return {
                    "likes": int(reactions),
                    "comments": int(comments),
                    "views": 0
                }
    except Exception as e:
        logger.warning(f"[Analytics] Meta stats pull failed for {post_url}: {e}")
    return {}

async def scrape_linkedin_stats_playwright(post_url: str) -> dict:
    """Headless Playwright session scraping for LinkedIn post metrics"""
    if not post_url or "skipped" in post_url or "local-only" in post_url:
        return {}
        
    # Standard LinkedIn cookies loading
    from playwright.async_api import async_playwright
    LI_COOKIES = os.path.join(REPO_ROOT, "linkedin_cookies", "linkedin_cookies.json")
    if not os.path.exists(LI_COOKIES):
        LI_COOKIES = os.path.join(REPO_ROOT, "linkedin_cookies.json")
        
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": PROXY_URL},
                args=["--no-sandbox", "--disable-gpu"]
            )
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            
            # Load cookies to view post logged-in (LinkedIn blocks guest feed views often)
            if os.path.exists(LI_COOKIES):
                with open(LI_COOKIES, encoding="utf-8") as f:
                    cookies_data = json.load(f)
                    if cookies_data.get("cookies"):
                        await ctx.add_cookies(cookies_data["cookies"])
                        
            page = await ctx.new_page()
            await page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Scrape reactions
            reactions = 0
            react_el = await page.query_selector(".social-details-social-counts__reactions-count, .social-details-social-counts__social-action-bubble")
            if react_el:
                react_text = await react_el.text_content()
                digits = re.findall(r"\d+", react_text.replace(",", "").replace(".", ""))
                if digits:
                    reactions = int(digits[0])
                    
            # Scrape comments
            comments = 0
            comm_el = await page.query_selector(".social-details-social-counts__comments")
            if comm_el:
                comm_text = await comm_el.text_content()
                digits = re.findall(r"\d+", comm_text.replace(",", "").replace(".", ""))
                if digits:
                    comments = int(digits[0])
                    
            await browser.close()
            return {
                "likes": reactions,
                "comments": comments,
                "views": 0
            }
    except Exception as e:
        logger.warning(f"[Analytics] Playwright scraping failed for LinkedIn {post_url}: {e}")
    return {}

def run_analytics_pull() -> dict:
    """Scans done.json, updates statistics for all platforms, and saves log"""
    logger.info("[Analytics] Pulling latest metrics from all platforms...")
    
    if not os.path.exists(DONE_PATH):
        logger.warning(f"done.json not found at {DONE_PATH}. Skipping metrics pull.")
        return {}
        
    try:
        with open(DONE_PATH, "r", encoding="utf-8") as f:
            done_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read done.json: {e}")
        return {}
        
    report = {}
    
    # Process only the 10 most recent posts to avoid heavy rate limits or slow crawls
    recent_topics = list(done_data.keys())[-10:]
    
    import asyncio
    
    for topic in recent_topics:
        item = done_data[topic]
        logger.info(f"[Analytics] Pulling stats for topic: '{topic}'")
        
        topic_stats = {
            "youtube": {},
            "facebook": {},
            "instagram": {},
            "linkedin": {}
        }
        
        # 1. YouTube Stats
        yt_url = item.get("youtube_url")
        if yt_url and "watch" in yt_url:
            topic_stats["youtube"] = fetch_youtube_stats(yt_url)
            
        # 2. Facebook Stats
        fb_url = item.get("facebook_url")
        if fb_url:
            topic_stats["facebook"] = fetch_meta_post_stats(fb_url, "facebook")
            
        # 3. Instagram Stats
        ig_url = item.get("instagram_url")
        if ig_url:
            topic_stats["instagram"] = fetch_meta_post_stats(ig_url, "instagram")
            
        # 4. LinkedIn Stats
        li_url = item.get("linkedin_url")
        if li_url and "linkedin.com" in li_url:
            # Run async scraping in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            topic_stats["linkedin"] = loop.run_until_complete(scrape_linkedin_stats_playwright(li_url))
            loop.close()
            
        report[topic] = topic_stats
        
    # Write analytics log
    os.makedirs(ANALYTICS_LOGS_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(ANALYTICS_LOGS_DIR, f"analytics_{today}.json")
    
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "metrics": report
            }, f, indent=2, ensure_ascii=False)
        logger.success(f"[Analytics] Saved performance metrics to: {log_path}")
    except Exception as e:
        logger.error(f"Failed to save analytics log: {e}")
        
    return report

def generate_analytics_summary_markdown(report: dict) -> str:
    """Produces a formatted terminal / markdown performance dashboard"""
    if not report:
        return "No analytics data pulled or available."
        
    lines = []
    lines.append("\n======================================================================")
    lines.append("                     DAILY PERFORMANCE DASHBOARD                      ")
    lines.append("======================================================================")
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for topic, platforms in report.items():
        lines.append(f"Post Topic: '{topic}'")
        lines.append("-" * 50)
        
        has_stats = False
        for platform, stats in platforms.items():
            if stats:
                has_stats = True
                views = stats.get("views", 0)
                likes = stats.get("likes", 0)
                comments = stats.get("comments", 0)
                
                # Format platform output
                views_str = f"Views: {views} | " if views > 0 else ""
                lines.append(f"  [{platform.upper()}]  {views_str}Likes: {likes} | Comments: {comments}")
                
        if not has_stats:
            lines.append("  (No performance stats pulled/available for this post yet)")
            
        lines.append("") # spacer
        
    lines.append("======================================================================")
    return "\n".join(lines)
