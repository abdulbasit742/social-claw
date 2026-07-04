import os
import re
from PIL import Image
from loguru import logger

def adapt_caption(platform: str, text: str, hashtags: list = None) -> str:
    """
    Format and adapt caption copy based on platform restrictions and styles:
    - youtube_shorts: Kept under 500 chars, hashtag-dense, short title structure.
    - instagram: Under 2200 chars, tags space, remove raw links (since they aren't clickable).
    - linkedin: Clean line-spacing, professional call-to-action, clickable links are kept.
    - facebook: Engaged tone, emoji friendly, clean links.
    """
    clean_text = text or ""
    tags = hashtags or []
    
    # Extract tags from text if not provided
    if not tags:
        found_tags = re.findall(r"#\w+", clean_text)
        if found_tags:
            tags = [t.replace("#", "") for t in found_tags]
            # Strip tags from main text to format separately
            clean_text = re.sub(r"#\w+", "", clean_text).strip()
            
    # Format platform hashtags string
    tags_str = " ".join([f"#{t}" for t in tags[:10]]) if tags else ""
    
    if platform == "youtube_shorts" or platform == "youtube":
        # Keep it concise
        desc = f"{clean_text}\n\n{tags_str}".strip()
        if len(desc) > 1000:
            desc = desc[:990] + "..."
        return desc
        
    elif platform == "instagram":
        # Instagram has 2200 character limit and links are non-clickable
        # Let's remove links from text
        no_links_text = re.sub(r"https?://\S+", "", clean_text).strip()
        desc = f"{no_links_text}\n\n{tags_str}".strip()
        if len(desc) > 2200:
            desc = desc[:2190] + "..."
        return desc
        
    elif platform == "linkedin":
        # LinkedIn supports clean long professional posts with linebreaks
        desc = f"{clean_text}\n\n{tags_str}".strip()
        if len(desc) > 3000:
            desc = desc[:2990] + "..."
        return desc
        
    elif platform == "facebook":
        # Facebook Page Post formatting
        desc = f"{clean_text}\n\n{tags_str}".strip()
        if len(desc) > 5000:
            desc = desc[:4990] + "..."
        return desc
        
    return f"{clean_text}\n\n{tags_str}".strip()

def adapt_image(image_path: str, platform: str) -> str:
    """
    Resize or pad a local image to standard platform ratios using PIL:
    - instagram: 1:1 Square (1080x1080)
    - linkedin: 4:5 Vertical or 1:1 Square (1080x1080)
    - facebook: 1:1 Square (1080x1080)
    """
    if not image_path or not os.path.exists(image_path):
        return image_path
        
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Decide target aspect ratio
        if platform in ["instagram", "facebook", "linkedin"]:
            # Target 1:1 square
            target_w, target_h = 1024, 1024
        else:
            return image_path # return as-is
            
        logger.info(f"[Cross-Post] Adapting image {os.path.basename(image_path)} size {width}x{height} to {target_w}x{target_h} ({platform})")
        
        # Resize/crop to fill or pad
        # For simplicity and high visual quality, pad to target square aspect ratio using black background
        square_img = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        
        # Resize keeping aspect ratio
        aspect = width / height
        if aspect > 1: # Landscape
            new_w = target_w
            new_h = int(target_w / aspect)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            offset = (0, (target_h - new_h) // 2)
        else: # Portrait
            new_h = target_h
            new_w = int(target_h * aspect)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            offset = ((target_w - new_w) // 2, 0)
            
        square_img.paste(resized, offset)
        
        # Save as adapted image in the same directory
        dir_name = os.path.dirname(image_path)
        base_name = os.path.basename(image_path)
        name, ext = os.path.splitext(base_name)
        adapted_path = os.path.join(dir_name, f"{name}_adapted_{platform}{ext}")
        
        square_img.save(adapted_path, quality=95)
        logger.success(f"[Cross-Post] Saved adapted image at: {adapted_path}")
        return adapted_path
        
    except Exception as e:
        logger.error(f"[Cross-Post] Failed to adapt image: {e}")
        return image_path
