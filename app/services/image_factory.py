import os
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
import sys
import json
import time
import urllib.request
import urllib.parse
import logging
import requests
from loguru import logger

# Ensure project root is on path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from app.services import meta_upload

PROXY_URL = "http://172.30.10.10:3128"
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

def load_factory_config():
    config_path = os.path.join(REPO_ROOT, "auto_factory.config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading factory config: {e}")
    return {}

def call_local_ollama(prompt: str) -> str:
    url = "http://127.0.0.1:11434/api/generate"
    data = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }
    try:
        req_data = json.dumps(data).encode("utf-8")
        proxy_support = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_support)
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with opener.open(req, timeout=120) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            return resp_data.get("response", "").strip()
    except Exception as e:
        logger.error(f"Ollama call failed in image_factory: {e}")
        return ""

def get_font(font_name="arial.ttf", size=32):
    import os
    try:
        from PIL import ImageFont
        return ImageFont.truetype(font_name, size)
    except Exception:
        try:
            # Fallback to system path on Windows
            from PIL import ImageFont
            win_font = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", font_name)
            if os.path.exists(win_font):
                return ImageFont.truetype(win_font, size)
        except Exception:
            pass
    from PIL import ImageFont
    return ImageFont.load_default()

def generate_quote_image(quote_text: str, author: str, output_path: str, branding_handle: str = "@pes_entrepreneur_society"):
    from PIL import Image, ImageDraw
    
    # 1. Create a 1080x1080 canvas with a sleek dark gradient
    width, height = 1080, 1080
    image = Image.new("RGB", (width, height), "#0f172a") # Dark Slate base
    draw = ImageDraw.Draw(image)
    
    # Draw simple gradient (Slate-950 to Slate-800)
    for y in range(height):
        # Linear interpolation between #090d16 (9, 13, 22) and #1e293b (30, 41, 59)
        r = int(9 + (y / height) * 21)
        g = int(13 + (y / height) * 28)
        b = int(22 + (y / height) * 37)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    # 2. Draw a beautiful subtle neon outline card in the center
    card_margin = 100
    # Draw a thin glassmorphic container outline
    draw.rectangle(
        [card_margin, card_margin, width - card_margin, height - card_margin],
        outline="#38bdf8", # Light Sky Blue
        width=2
    )
    
    # 3. Draw premium decorative quote marks
    quote_font = get_font("arial.ttf", 96)
    draw.text((card_margin + 50, card_margin + 30), "“", fill="#38bdf8", font=quote_font)
    
    # 4. Wrap and render the quote text
    text_font = get_font("arial.ttf", 44)
    words = quote_text.split()
    lines = []
    current_line = []
    max_line_width = 700 # px
    
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        try:
            line_w = draw.textlength(line_str, font=text_font)
        except AttributeError:
            line_w = draw.textsize(line_str, font=text_font)[0]
            
        if line_w > max_line_width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(" ".join(current_line))
                current_line = []
                
    if current_line:
        lines.append(" ".join(current_line))
        
    try:
        line_height = draw.textsize("A", font=text_font)[1] * 1.5
    except AttributeError:
        line_height = 44 * 1.5
        
    total_text_height = len(lines) * line_height
    start_y = (height - total_text_height) // 2
    
    # Draw lines
    for i, line in enumerate(lines):
        try:
            w = draw.textlength(line, font=text_font)
        except AttributeError:
            w = draw.textsize(line, font=text_font)[0]
            
        x = (width - w) // 2
        draw.text((x, start_y + i * line_height), line, fill="#ffffff", font=text_font)
        
    # 5. Draw the Author (Steve Jobs, Elon Musk, etc.)
    author_font = get_font("arial.ttf", 36)
    author_str = f"— {author}"
    try:
        author_w = draw.textlength(author_str, font=author_font)
    except AttributeError:
        author_w = draw.textsize(author_str, font=author_font)[0]
        
    draw.text(
        ((width - author_w) // 2, start_y + total_text_height + 40),
        author_str,
        fill="#94a3b8", # Muted Slate
        font=author_font
    )
    
    # 6. Draw branding handle at the bottom center
    handle_font = get_font("arial.ttf", 28)
    try:
        handle_w = draw.textlength(branding_handle, font=handle_font)
    except AttributeError:
        handle_w = draw.textsize(branding_handle, font=handle_font)[0]
        
    draw.text(
        ((width - handle_w) // 2, height - card_margin - 50),
        branding_handle,
        fill="#38bdf8", # Accent Blue
        font=handle_font
    )
    
    image.save(output_path, "JPEG", quality=95)
    logger.info(f"Generated quote image saved to: {output_path}")

def brainstorm_image_post(niche: str) -> dict:
    """
    Brainstorms a success/motivation quote, its author, and a viral caption.
    """
    prompt = f"""
    You are a viral social media manager for a page in the niche: "{niche}".
    We want to generate a highly engaging minimalist quote graphic for Facebook and Instagram.
    
    Return a JSON object containing:
    1. "topic": A brief name of the topic.
    2. "quote": A powerful, inspirational, and highly viral business/startup success quote. Keep it under 25 words.
    3. "author": The name of the author who said this quote.
    4. "caption": A highly engaging, viral caption for the post. Include a hook, 2-3 valuable tips expanding on the quote, a call to action, and 5-8 relevant viral hashtags.
    
    Response format must be ONLY raw JSON. Do not include markdown wraps or code blocks.
    JSON structure:
    {{
      "topic": "...",
      "quote": "...",
      "author": "...",
      "caption": "..."
    }}
    """
    
    resp = call_local_ollama(prompt)
    if not resp:
        return {}
    
    if resp.startswith("```json"):
        resp = resp.replace("```json", "", 1)
    if resp.endswith("```"):
        resp = resp[:-3]
    resp = resp.strip()
    
    try:
        return json.loads(resp)
    except Exception as je:
        logger.error(f"Failed to parse Ollama JSON response: {je}. Raw output was: {resp}")
        return {
            "topic": "Consistency",
            "quote": "Consistency is what transforms average into excellence.",
            "author": "Anonymous",
            "caption": "Consistency is key to success! 🚀\n\n💡 Build daily habits\n💡 Focus on long-term goals\n💡 Push through obstacles\n\nTag a founder! #success #consistency #entrepreneur #startups"
        }

def run_image_post_flow(custom_topic: str = None) -> dict:
    """
    Orchestrates the entire image generation and posting flow.
    """
    logger.info("Starting Image Post Flow...")
    
    # Bypass system proxies for direct external API connections
    os.environ["HTTP_PROXY"] = ""
    os.environ["HTTPS_PROXY"] = ""
    os.environ["http_proxy"] = ""
    os.environ["https_proxy"] = ""
    
    # 1. Load config
    config = load_factory_config()
    niche = config.get("niche", "entrepreneurship, startups, business success and money mindset")
    
    # 2. Brainstorm topic, image prompt, and caption
    post_data = brainstorm_image_post(niche)
    if not post_data:
        logger.error("Brainstorming failed.")
        return {"success": False, "error": "Brainstorming failed"}
        
    if custom_topic:
        post_data["topic"] = custom_topic
        
    topic = post_data.get("topic", "Niche Success")
    quote = post_data.get("quote", "")
    author = post_data.get("author", "Anonymous")
    caption = post_data.get("caption", "")
    
    logger.info(f"Topic: {topic}")
    logger.info(f"Quote: {quote}")
    logger.info(f"Author: {author}")
    logger.info(f"Caption:\n{caption}")
    
    # 3. Generate minimalist quote image locally
    temp_image_path = os.path.join(REPO_ROOT, f"temp_post_image_{int(time.time())}.jpg")
    try:
        logger.info("Generating quote image locally...")
        generate_quote_image(quote, author, temp_image_path)
        logger.success(f"Generated quote image successfully: {temp_image_path}")
    except Exception as e:
        logger.error(f"Failed to generate quote image locally: {e}")
        return {"success": False, "error": f"Local image generation failed: {e}"}
        
    # 4. Upload to Facebook Page
    fb_res = None
    if config.get("post_facebook", True):
        try:
            fb_res = meta_upload.upload_image_to_facebook(temp_image_path, caption)
        except Exception as fe:
            logger.error(f"Facebook image upload failed: {fe}")
            
    # 5. Upload to Instagram
    ig_res = None
    if config.get("post_instagram", True):
        try:
            ig_res = meta_upload.upload_image_to_instagram(temp_image_path, caption)
        except Exception as ie:
            logger.error(f"Instagram image upload failed: {ie}")
            
    # 6. Cleanup
    if os.path.exists(temp_image_path):
        try:
            os.remove(temp_image_path)
            logger.info("Cleaned up temporary generated image file")
        except: pass
        
    return {
        "success": True,
        "topic": topic,
        "facebook_post": fb_res,
        "instagram_post": ig_res
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run_image_post_flow()
    print("Execution Result:", json.dumps(res, indent=2))
