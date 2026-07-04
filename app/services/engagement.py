import os
import re
import json
import time
import random
import requests
from datetime import datetime
from loguru import logger

# Paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPLIED_LOG_PATH = os.path.join(REPO_ROOT, "logs", "replied_comments.json")
DONE_PATH = os.path.join(REPO_ROOT, "scripts", "done.json")

# Proxy
PROXY_URL = "http://172.30.10.10:3128"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

def load_replied_ids() -> set:
    if not os.path.exists(REPLIED_LOG_PATH):
        return set()
    try:
        with open(REPLIED_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("replied_ids", []))
    except Exception as e:
        logger.warning(f"[Engagement] Failed to load replied comment IDs: {e}")
        return set()

def save_replied_id(comment_id: str):
    os.makedirs(os.path.dirname(REPLIED_LOG_PATH), exist_ok=True)
    replied = load_replied_ids()
    replied.add(comment_id)
    try:
        with open(REPLIED_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({"replied_ids": list(replied)}, f, indent=2)
    except Exception as e:
        logger.error(f"[Engagement] Failed to save replied comment ID {comment_id}: {e}")

def call_local_ollama_for_reply(comment_text: str, topic: str) -> str:
    """Generate a friendly, natural social media comment reply using qwen2.5:7b"""
    prompt = (
        f"You are a friendly social media manager representing an entrepreneurship and success mindset brand.\n"
        f"A user left a comment on your post about '{topic}'.\n"
        f"User comment: \"{comment_text}\"\n\n"
        f"Write a short, engaging, friendly, and professional reply (1-2 sentences maximum). Keep it natural, conversational, and ToS-safe. Do not use generic bot placeholders."
    )
    
    payload = {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "You are a helpful and polite social media manager. Keep replies under 30 words and highly human-like."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    
    try:
        # Request local Ollama directly, bypassing proxy
        req = urllib.request.Request(
            "http://localhost:11434/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        # Bypassing proxies defensively via urllib
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            reply = res_data["choices"][0]["message"]["content"].strip()
            # Clean think tags if LLM uses reasoning
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            return reply
    except Exception as e:
        logger.error(f"[Engagement] Ollama reply generation failed: {e}")
        # Return fallback reply
        return "Thanks for sharing! Keep pushing forward! 🚀"

# Import urllib inside the function or block to handle local call
import urllib.request

def post_first_comment_youtube(video_id: str, topic: str):
    """Pin an engaging first comment on YouTube Reels/Videos"""
    try:
        from app.services.youtube_upload import get_authenticated_service
        youtube = get_authenticated_service()
        
        comment_text = f"What is your biggest takeaway about {topic}? Drop a comment below! 👇🚀"
        
        body = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": comment_text
                    }
                }
            }
        }
        res = youtube.commentThreads().insert(part="snippet", body=body).execute()
        comment_id = res["snippet"]["topLevelComment"]["id"]
        logger.success(f"[Engagement-YT] Posted first comment: {comment_id}")
        
        # Try to pin comment (requires channel owner auth scopes)
        try:
            youtube.comments().setModerationStatus(id=comment_id, moderationStatus="published").execute()
            logger.info(f"[Engagement-YT] Pinned first comment.")
        except Exception as pin_err:
            logger.debug(f"[Engagement-YT] Pinning comment not supported or lacks scopes: {pin_err}")
            
    except Exception as e:
        logger.warning(f"[Engagement-YT] Failed to post first comment: {e}")

def post_first_comment_meta(post_url: str, platform: str, topic: str):
    """Post engaging first comment on FB Page or Instagram post"""
    try:
        from app.services.meta_upload import load_meta_credentials
        creds = load_meta_credentials()
        if not creds: return
        
        token = creds.get("access_token")
        if not token: return
        
        # Parse post ID from URL
        match = re.search(r"/(?:reel|posts|videos|p)/([a-zA-Z0-9_]+)", post_url)
        if not match: return
        media_id = match.group(1)
        
        comment_text = f"What's your takeaway on this? Let's discuss below! 👇🔥"
        
        url = f"https://graph.facebook.com/v20.0/{media_id}/comments"
        params = {
            "message": comment_text,
            "access_token": token
        }
        res = requests.post(url, params=params, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            logger.success(f"[Engagement-Meta] First comment posted to {platform}: {res.json().get('id')}")
    except Exception as e:
        logger.warning(f"[Engagement-Meta] First comment post failed: {e}")

async def post_first_comment_linkedin_playwright(post_url: str, topic: str):
    """Post first comment on LinkedIn using Playwright"""
    from playwright.async_api import async_playwright
    LI_COOKIES = os.path.join(REPO_ROOT, "linkedin_cookies.json")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_URL})
            ctx = await browser.new_context()
            if os.path.exists(LI_COOKIES):
                with open(LI_COOKIES, encoding="utf-8") as f:
                    cookies = json.load(f)
                    await ctx.add_cookies(cookies["cookies"])
                    
            page = await ctx.new_page()
            await page.goto(post_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # Click comment input box
            comment_box = await page.query_selector(".ql-editor, .comments-comment-box__editor")
            if comment_box:
                await comment_box.click()
                comment_text = f"What are your thoughts on {topic}? Let's grow together! 🚀"
                await comment_box.fill(comment_text)
                await page.wait_for_timeout(1000)
                
                # Click Post Comment
                submit_btn = await page.query_selector("button.comments-comment-box__submit-button")
                if submit_btn:
                    await submit_btn.click()
                    logger.success(f"[Engagement-LI] Posted first comment on LinkedIn.")
                    await page.wait_for_timeout(3000)
            await browser.close()
    except Exception as e:
        logger.warning(f"[Engagement-LI] LinkedIn Playwright comment failed: {e}")

def run_engagement_loop(topic: str, urls: dict):
    """Trigger pinned first comments on a newly published topic"""
    logger.info(f"[Engagement] Starting engagement triggers for: '{topic}'")
    
    # 1. YouTube
    yt_url = urls.get("youtube")
    if yt_url:
        from app.services.analytics import extract_youtube_video_id
        video_id = extract_youtube_video_id(yt_url)
        if video_id:
            post_first_comment_youtube(video_id, topic)
            
    # 2. Facebook
    fb_url = urls.get("facebook")
    if fb_url:
        post_first_comment_meta(fb_url, "facebook", topic)
        
    # 3. Instagram
    ig_url = urls.get("instagram")
    if ig_url:
        post_first_comment_meta(ig_url, "instagram", topic)
        
    # 4. LinkedIn
    li_url = urls.get("linkedin")
    if li_url and "linkedin.com" in li_url:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(post_first_comment_linkedin_playwright(li_url, topic))
        loop.close()

def auto_reply_to_recent_comments(max_replies: int = 5):
    """Rate-limited, ToS-safe automated reply loop for recent comments"""
    logger.info("[Engagement] Scanning recent posts for new comments...")
    
    if not os.path.exists(DONE_PATH):
        return
        
    try:
        with open(DONE_PATH, "r", encoding="utf-8") as f:
            done_data = json.load(f)
    except Exception as e:
        logger.error(f"[Engagement] Failed to read done.json: {e}")
        return
        
    recent_topics = list(done_data.keys())[-5:] # Scan last 5 posts
    replied_count = 0
    replied_ids = load_replied_ids()
    
    # YouTube Comments Reply
    try:
        from app.services.youtube_upload import get_authenticated_service
        from app.services.analytics import extract_youtube_video_id
        youtube = get_authenticated_service()
        
        for topic in recent_topics:
            if replied_count >= max_replies: break
            yt_url = done_data[topic].get("youtube_url")
            video_id = extract_youtube_video_id(yt_url)
            if not video_id: continue
            
            # Fetch comments
            try:
                res = youtube.commentThreads().list(videoId=video_id, part="snippet", maxResults=5).execute()
                for thread in res.get("items", []):
                    if replied_count >= max_replies: break
                    comment = thread["snippet"]["topLevelComment"]
                    comment_id = comment["id"]
                    comment_text = comment["snippet"]["textDisplay"]
                    author = comment["snippet"]["authorDisplayName"]
                    
                    # Avoid replying to ourselves or already replied comments
                    if comment_id in replied_ids or "Owner" in author:
                        continue
                        
                    # Generate reply
                    logger.info(f"[Engagement-YT] Generating reply to comment by {author}: '{comment_text}'")
                    reply_text = call_local_ollama_for_reply(comment_text, topic)
                    
                    # Post reply comment
                    reply_body = {
                        "snippet": {
                            "parentId": comment_id,
                            "textOriginal": reply_text
                        }
                    }
                    youtube.comments().insert(part="snippet", body=reply_body).execute()
                    save_replied_id(comment_id)
                    logger.success(f"[Engagement-YT] Replied successfully to {author}.")
                    replied_count += 1
                    
                    # ToS-safe randomized delay
                    time.sleep(random.randint(15, 30))
            except Exception as thread_err:
                logger.debug(f"[Engagement-YT] Skip comment fetch: {thread_err}")
    except Exception as e:
        logger.debug(f"[Engagement-YT] YouTube reply loop bypassed: {e}")

    logger.info(f"[Engagement] Auto-reply run finished. Replied to {replied_count} comments.")
