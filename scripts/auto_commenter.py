import os
import sys
import json
import time
import random
import re
import urllib.request
import argparse
from loguru import logger
from playwright.async_api import async_playwright

project_root = r"C:\Users\absh5\MoneyPrinterTurbo"
sys.path.append(project_root)

LI_COOKIES = os.path.join(project_root, "linkedin_cookies.json")
IG_COOKIES = os.path.join(project_root, "instagram_cookies.json")
FB_COOKIES = os.path.join(project_root, "fb_cookies.json")
TT_COOKIES = os.path.join(project_root, "tiktok_storage_state.json")
if not os.path.exists(TT_COOKIES):
    TT_COOKIES = os.path.join(project_root, "tiktok_cookies.json")

TRACKER_FILE = os.path.join(project_root, "storage", "commented_posts.json")
PROXY = "http://172.30.10.10:3128"

def load_commented_tracker() -> dict:
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load tracker: {e}")
    return {"linkedin": [], "instagram": [], "facebook": [], "tiktok": []}

def save_commented_tracker(tracker: dict):
    try:
        with open(TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(tracker, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save tracker: {e}")

def generate_comment_with_ollama(post_text: str, platform: str) -> str:
    cleaned_post = post_text[:400].replace('"', "'").strip()
    prompt = (
        f"You are a supportive, knowledgeable entrepreneur and business mentor.\n"
        f"Generate a friendly, natural, and insightful comment for this social media post on {platform}.\n"
        f"Post content: \"{cleaned_post}\"\n\n"
        f"Rules:\n"
        f"- Keep it under 25 words.\n"
        f"- Sound completely human and professional (avoid robotic phrases like 'nice post', 'great job').\n"
        f"- Add value or relate to the post content.\n"
        f"- Do not use hashtags."
    )
    payload = {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "You are a professional business coach. Keep comments short, engaging, and under 25 words."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    try:
        proxy_support = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_support)
        req = urllib.request.Request(
            "http://127.0.0.1:11434/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with opener.open(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            reply = res_data["choices"][0]["message"]["content"].strip()
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            reply = reply.strip('"').strip("'")
            return reply
    except Exception as e:
        logger.warning(f"Ollama comment generation failed: {e}. Using fallback comment.")
        fallbacks = [
            "Incredible perspective. Execution and consistency are key to building any successful venture! 🚀",
            "This is spot on. Building a startup is all about solving real problems day in and day out.",
            "Love this insights! Success is built on persistent daily efforts. Keep scaling! 🔥",
            "Very well said. The entrepreneur's journey is tough but extremely rewarding."
        ]
        return random.choice(fallbacks)

async def comment_on_linkedin(page, tracker, dry_run=False):
    logger.info("[LinkedIn] Fetching latest posts for #entrepreneurship...")
    await page.goto("https://www.linkedin.com/search/results/content/?keywords=entrepreneurship&sortBy=%22date_posted%22", wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)
    
    # Try multiple selectors to ensure posts are captured correctly
    posts = await page.query_selector_all(".reusable-search__result-container, .search-results-container article, div[data-urn]")
    if not posts:
        logger.warning("[LinkedIn] No posts found. Trying alternative selectors...")
        posts = await page.query_selector_all(".feed-shared-update-v2")
        
    commented_count = 0
    for i, post in enumerate(posts[:3]):
        try:
            post_text_elem = await post.query_selector(".feed-shared-update-v2__description, .break-words, .feed-shared-text")
            post_text = await post_text_elem.inner_text() if post_text_elem else "entrepreneurship and business tips"
            
            post_hash = str(hash(post_text))
            if post_hash in tracker["linkedin"]:
                logger.info(f"[LinkedIn] Already commented on post {i+1}, skipping.")
                continue
                
            logger.info(f"[LinkedIn] Post {i+1} text snippet: {post_text[:100]}...")
            comment_text = generate_comment_with_ollama(post_text, "LinkedIn")
            logger.info(f"[LinkedIn] Generated comment: \"{comment_text}\"")
            
            if dry_run:
                logger.info("[LinkedIn] DRY RUN: Bypassing actual comment submit.")
                tracker["linkedin"].append(post_hash)
                commented_count += 1
                continue
                
            comment_box = await post.query_selector(".ql-editor[contenteditable='true'], .comments-comment-box__editor")
            if comment_box:
                await comment_box.click()
                await comment_box.fill(comment_text)
                await page.wait_for_timeout(2000)
                
                submit_btn = await post.query_selector("button.comments-comment-box__submit-button")
                if submit_btn:
                    await submit_btn.click()
                    logger.success(f"[LinkedIn] Successfully commented on post {i+1}!")
                    tracker["linkedin"].append(post_hash)
                    commented_count += 1
                    await page.wait_for_timeout(random.randint(15000, 30000))
                else:
                    logger.warning("[LinkedIn] Submit button not found.")
            else:
                logger.warning("[LinkedIn] Comment edit area not found.")
        except Exception as post_err:
            logger.error(f"[LinkedIn] Error commenting on post {i+1}: {post_err}")
    return commented_count

async def comment_on_instagram(page, tracker, dry_run=False):
    logger.info("[Instagram] Navigating to explore hashtag entrepreneurship...")
    # Tag page selector is robust on desktop
    await page.goto("https://www.instagram.com/explore/tags/entrepreneurship/", wait_until="domcontentloaded")
    await page.wait_for_timeout(7000)
    
    # Instagram layout could use different class paths, let's target any links pointing to posts
    posts = await page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
    if not posts:
        logger.warning("[Instagram] No posts found on tag page. Trying explore page fallback...")
        await page.goto("https://www.instagram.com/explore/", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        posts = await page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
        
    if not posts:
        logger.warning("[Instagram] No posts found at all.")
        return 0
        
    commented_count = 0
    await posts[0].click()
    await page.wait_for_timeout(4000)
    
    for i in range(3):
        try:
            url = page.url
            if url in tracker["instagram"]:
                logger.info(f"[Instagram] Already commented on {url}, skipping.")
            else:
                caption_elem = await page.query_selector("h1, div[class*='Comment'] span, article span")
                post_text = await caption_elem.inner_text() if caption_elem else "business mindset"
                
                comment_text = generate_comment_with_ollama(post_text, "Instagram")
                logger.info(f"[Instagram] Generated comment for {url}: \"{comment_text}\"")
                
                if dry_run:
                    logger.info("[Instagram] DRY RUN: Bypassing actual comment submit.")
                    tracker["instagram"].append(url)
                    commented_count += 1
                else:
                    comment_box = await page.query_selector("textarea[aria-label*='comment'], textarea[placeholder*='comment']")
                    if comment_box:
                        await comment_box.click()
                        await comment_box.fill(comment_text)
                        await page.wait_for_timeout(2000)
                        
                        submit_btn = await page.query_selector("div[role='button']:has-text('Post'), button:has-text('Post')")
                        if submit_btn:
                            await submit_btn.click()
                            logger.success(f"[Instagram] Successfully commented on post!")
                            tracker["instagram"].append(url)
                            commented_count += 1
                            await page.wait_for_timeout(random.randint(15000, 30000))
                        else:
                            logger.warning("[Instagram] Post button not found.")
                    else:
                        logger.warning("[Instagram] Comment textarea not found.")
            
            next_btn = await page.query_selector("svg[aria-label='Next'], svg[aria-label='Right chevron'], .coreSpriteRightPaginationArrow")
            if next_btn:
                await next_btn.click()
                await page.wait_for_timeout(4000)
            else:
                break
        except Exception as post_err:
            logger.error(f"[Instagram] Error on Instagram post loop: {post_err}")
            break
    return commented_count

async def comment_on_facebook(page, tracker, dry_run=False):
    logger.info("[Facebook] Navigating to search posts for entrepreneurship...")
    await page.goto("https://www.facebook.com/search/posts?q=entrepreneurship", wait_until="domcontentloaded")
    await page.wait_for_timeout(6000)
    
    posts = await page.query_selector_all("div[role='article'], div[class*='feed_story']")
    commented_count = 0
    for i, post in enumerate(posts[:2]):
        try:
            post_text_elem = await post.query_selector("div[data-ad-preview='message'], div[class*='userContent'], div[dir='auto']")
            post_text = await post_text_elem.inner_text() if post_text_elem else "user posted entrepreneurship topic"
            
            post_hash = str(hash(post_text))
            if post_hash in tracker["facebook"]:
                logger.info(f"[Facebook] Already commented on post {i+1}, skipping.")
                continue
                
            comment_text = generate_comment_with_ollama(post_text, "Facebook")
            logger.info(f"[Facebook] Generated comment: \"{comment_text}\"")
            
            if dry_run:
                logger.info("[Facebook] DRY RUN: Bypassing actual comment submit.")
                tracker["facebook"].append(post_hash)
                commented_count += 1
                continue
                
            comment_box = await post.query_selector("div[aria-label*='Comment'], div[role='textbox'], div[aria-label*='comment']")
            if comment_box:
                await comment_box.click()
                await comment_box.fill(comment_text)
                await page.wait_for_timeout(2000)
                await page.keyboard.press("Enter")
                logger.success(f"[Facebook] Successfully commented on post {i+1}!")
                tracker["facebook"].append(post_hash)
                commented_count += 1
                await page.wait_for_timeout(random.randint(15000, 30000))
            else:
                logger.warning("[Facebook] Comment edit area not found.")
        except Exception as post_err:
            logger.error(f"[Facebook] Error on FB post {i+1}: {post_err}")
    return commented_count

async def comment_on_tiktok(page, tracker, dry_run=False):
    logger.info("[TikTok] Navigating to search entrepreneurship videos...")
    await page.goto("https://www.tiktok.com/search/video?q=entrepreneurship", wait_until="domcontentloaded")
    await page.wait_for_timeout(6000)
    
    video_cards = await page.query_selector_all("div[data-e2e='search_video-item'], div[class*='DivItemContainer'], div[class*='DivVideoCardContainer']")
    if not video_cards:
        logger.warning("[TikTok] No video cards found. Trying list items...")
        video_cards = await page.query_selector_all("a[href*='/video/']")
        
    if not video_cards:
        logger.warning("[TikTok] No video cards found.")
        return 0
        
    commented_count = 0
    await video_cards[0].click()
    await page.wait_for_timeout(4000)
    
    for i in range(2):
        try:
            url = page.url
            if url in tracker["tiktok"]:
                logger.info(f"[TikTok] Already commented on video {url}, skipping.")
            else:
                caption_elem = await page.query_selector("h1, div[data-e2e='browse-video-desc'], div[class*='DivDescription']")
                post_text = await caption_elem.inner_text() if caption_elem else "startup entrepreneurship video"
                
                comment_text = generate_comment_with_ollama(post_text, "TikTok")
                logger.info(f"[TikTok] Generated comment: \"{comment_text}\"")
                
                if dry_run:
                    logger.info("[TikTok] DRY RUN: Bypassing actual comment submit.")
                    tracker["tiktok"].append(url)
                    commented_count += 1
                else:
                    comment_box = await page.query_selector("div[data-e2e='comment-input'] div[contenteditable='true'], div[class*='DivCommentInput'] div[contenteditable='true']")
                    if comment_box:
                        await comment_box.click()
                        await comment_box.fill(comment_text)
                        await page.wait_for_timeout(2000)
                        
                        submit_btn = await page.query_selector("div[data-e2e='comment-post'], button[data-e2e='comment-post']")
                        if submit_btn:
                            await submit_btn.click()
                            logger.success(f"[TikTok] Successfully commented on TikTok video!")
                            tracker["tiktok"].append(url)
                            commented_count += 1
                            await page.wait_for_timeout(random.randint(15000, 30000))
                        else:
                            logger.warning("[TikTok] Post button not found.")
                    else:
                        logger.warning("[TikTok] Comment edit area not found.")
            
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(4000)
        except Exception as post_err:
            logger.error(f"[TikTok] Error in TikTok loop: {post_err}")
            break
    return commented_count

async def main():
    parser = argparse.ArgumentParser(description="Auto-Commenting Engagement Bot")
    parser.add_argument("--dry-run", action="store_true", help="Generate comments and dry run without posting")
    args = parser.parse_args()
    
    tracker = load_commented_tracker()
    logger.info("Initializing Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        # 1. LinkedIn
        if os.path.exists(LI_COOKIES):
            try:
                ctx = await browser.new_context(viewport={"width": 1366, "height": 768})
                with open(LI_COOKIES, encoding="utf-8") as f:
                    cookies = json.load(f)
                    await ctx.add_cookies(cookies.get("cookies", []))
                page = await ctx.new_page()
                count = await comment_on_linkedin(page, tracker, args.dry_run)
                logger.info(f"[LinkedIn] Finished. Total comments: {count}")
                await ctx.close()
            except Exception as e:
                logger.error(f"[LinkedIn] Auto comment failed: {e}")
                
        # 2. Instagram
        if os.path.exists(IG_COOKIES):
            try:
                ctx = await browser.new_context(viewport={"width": 1366, "height": 768})
                with open(IG_COOKIES, encoding="utf-8") as f:
                    cookies = json.load(f)
                    await ctx.add_cookies(cookies if isinstance(cookies, list) else cookies.get("cookies", []))
                page = await ctx.new_page()
                count = await comment_on_instagram(page, tracker, args.dry_run)
                logger.info(f"[Instagram] Finished. Total comments: {count}")
                await ctx.close()
            except Exception as e:
                logger.error(f"[Instagram] Auto comment failed: {e}")
                
        # 3. Facebook
        if os.path.exists(FB_COOKIES):
            try:
                ctx = await browser.new_context(viewport={"width": 1366, "height": 768})
                with open(FB_COOKIES, encoding="utf-8") as f:
                    cookies = json.load(f)
                    await ctx.add_cookies(cookies if isinstance(cookies, list) else cookies.get("cookies", []))
                page = await ctx.new_page()
                count = await comment_on_facebook(page, tracker, args.dry_run)
                logger.info(f"[Facebook] Finished. Total comments: {count}")
                await ctx.close()
            except Exception as e:
                logger.error(f"[Facebook] Auto comment failed: {e}")
                
        # 4. TikTok
        if os.path.exists(TT_COOKIES):
            try:
                ctx = await browser.new_context(viewport={"width": 1366, "height": 768})
                with open(TT_COOKIES, encoding="utf-8") as f:
                    cookies = json.load(f)
                    if "cookies" in cookies:
                        await ctx.add_cookies(cookies["cookies"])
                    else:
                        await ctx.add_cookies(cookies)
                page = await ctx.new_page()
                count = await comment_on_tiktok(page, tracker, args.dry_run)
                logger.info(f"[TikTok] Finished. Total comments: {count}")
                await ctx.close()
            except Exception as e:
                logger.error(f"[TikTok] Auto comment failed: {e}")
                
        await browser.close()
        
    save_commented_tracker(tracker)
    logger.success("Auto Commenter execution completed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
