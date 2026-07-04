import os
import sys
import json
import time
from loguru import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Enforce environment variables defensively
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

# Force stdout to UTF-8 on Windows to prevent cp1252 logging crash
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.services.tiktok_upload import upload_to_tiktok, check_tiktok_credentials
from app.services.llm import generate_social_metadata

DONE_PATH = os.path.join(PROJECT_ROOT, "scripts", "done.json")

def catchup_tiktok():
    logger.info("Starting TikTok Catch-up Script...")
    
    # 1. Check credentials first
    status = check_tiktok_credentials()
    if status not in ["ok", "refreshed"]:
        logger.error(f"TikTok credentials not valid: {status}. Exiting catch-up.")
        return
        
    if not os.path.exists(DONE_PATH):
        logger.error(f"done.json not found at {DONE_PATH}")
        return
        
    try:
        with open(DONE_PATH, "r", encoding="utf-8") as f:
            done_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read done.json: {e}")
        return

    logger.info(f"Loaded {len(done_data)} total entries from done.json")
    
    uploaded_count = 0
    
    for topic, entry in list(done_data.items()):
        # Check if it has a local video path
        video_path = entry.get("local_video_path")
        if not video_path:
            continue
            
        if not os.path.exists(video_path):
            logger.warning(f"Video file for '{topic}' not found at {video_path}, skipping.")
            continue
            
        # Check if TikTok URL is missing or not posted
        tk_url = entry.get("tiktok_url")
        is_posted = tk_url and tk_url.startswith("http") and "local-only" not in tk_url
        
        if not is_posted:
            logger.info(f"Found pending TikTok upload for topic: '{topic}' at path: {video_path}")
            
            # Generate TikTok caption
            script = entry.get("script", "")
            try:
                meta = generate_social_metadata(topic, script, platform="tiktok")
                tk_caption = f"{meta.get('title', '')} " + " ".join(meta.get('hashtags', []))
            except Exception as e:
                logger.warning(f"Failed to generate TikTok metadata: {e}. Using fallback caption.")
                tk_caption = f"{topic} #startup #business #entrepreneur"
                
            logger.info(f"Caption: {tk_caption}")
            
            # Upload to TikTok
            res = upload_to_tiktok(video_path, tk_caption)
            if res and res.get("url"):
                tiktok_url = res.get("url")
                logger.success(f"Successfully uploaded '{topic}' to TikTok! URL: {tiktok_url}")
                entry["tiktok_url"] = tiktok_url
                done_data[topic] = entry
                
                # Save updated done.json immediately after each upload
                with open(DONE_PATH, "w", encoding="utf-8") as f:
                    json.dump(done_data, f, indent=2, ensure_ascii=False)
                    
                uploaded_count += 1
                # Cooldown delay to avoid spamming
                logger.info("Waiting 30 seconds before next upload...")
                time.sleep(30)
            else:
                logger.error(f"Failed to upload '{topic}' to TikTok.")
                entry["tiktok_url"] = "failed"
                with open(DONE_PATH, "w", encoding="utf-8") as f:
                    json.dump(done_data, f, indent=2, ensure_ascii=False)

    logger.success(f"TikTok catch-up completed. Uploaded {uploaded_count} videos.")

if __name__ == "__main__":
    catchup_tiktok()
