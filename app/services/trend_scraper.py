import os
import json
import random
from loguru import logger
from playwright.async_api import async_playwright

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TT_STORAGE = os.path.join(project_root, "tiktok_storage_state.json")
PROXY = "http://172.30.10.10:3128"

async def get_tiktok_trends(topic="entrepreneurship", max_posts=3):
    """Scrapes top trending captions from TikTok for a specific hashtag."""
    logger.info(f"[Scraper] Fetching TikTok trends for #{topic}")
    trends = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        ctx_kwargs = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1366, "height": 768},
            "locale": "en-US"
        }
        
        if os.path.exists(TT_STORAGE):
            ctx_kwargs["storage_state"] = TT_STORAGE
            
        ctx = await browser.new_context(**ctx_kwargs)
        page = await ctx.new_page()
        
        try:
            url = f"https://www.tiktok.com/search/video?q={topic}"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            
            # Extract video captions/descriptions
            elements = await page.query_selector_all('div[data-e2e="search-card-video-caption"]')
            if not elements:
                elements = await page.query_selector_all('.search-result-video-container div')
                
            for i, el in enumerate(elements[:max_posts]):
                text = await el.inner_text()
                text = text.replace('\n', ' ').strip()
                if text:
                    trends.append(f"TikTok Viral Concept {i+1}: {text}")
                    
        except Exception as e:
            logger.error(f"[Scraper] TikTok scrape failed: {e}")
            
        await browser.close()
        
    return trends

async def get_social_trends():
    """Aggregates trending concepts from social media platforms."""
    topics = ["entrepreneurship", "startup", "business", "sidehustle"]
    chosen_topic = random.choice(topics)
    
    logger.info(f"[Scraper] Aggregating viral concepts for topic: {chosen_topic}")
    
    # Currently only scraping TikTok. In the future, LinkedIn and FB can be added here.
    tt_trends = await get_tiktok_trends(chosen_topic)
    
    context = "\n".join(tt_trends)
    if not context.strip():
        return f"Talk about some fresh and unique strategies for {chosen_topic}."
        
    return f"Here are some viral concepts recently trending around {chosen_topic}:\n" + context

if __name__ == "__main__":
    import asyncio
    trends = asyncio.run(get_social_trends())
    print("\n--- SCRAPED TRENDS ---")
    print(trends)
