import os
import json
import requests
from typing import Optional
from loguru import logger
from app.config import config

CREDENTIALS_PATH = "telegram_credentials.json"
PROXIES = config.proxy

def load_telegram_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        return {}
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def check_telegram_credentials() -> str:
    creds = load_telegram_credentials()
    if not creds.get("bot_token") or not creds.get("chat_id"):
        return "skipped-missing"
    
    # Check validity via getMe
    url = f"https://api.telegram.org/bot{creds['bot_token']}/getMe"
    try:
        res = requests.get(url, proxies=PROXIES, timeout=10)
        if res.status_code == 200 and res.json().get("ok"):
            return "ok"
        return "skipped-expired"
    except Exception as e:
        logger.error(f"Telegram Bot credentials check error: {e}")
        return "skipped-expired"

def upload_to_telegram(video_path: str, caption: str) -> Optional[dict]:
    creds = load_telegram_credentials()
    bot_token = creds.get("bot_token")
    chat_id = creds.get("chat_id")
    
    if not bot_token or not chat_id:
        logger.error("Telegram upload failed: bot_token or chat_id missing.")
        return None
        
    if not os.path.exists(video_path):
        logger.error(f"Telegram upload failed: Video file not found: {video_path}")
        return None
        
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    try:
        logger.info(f"Uploading video to Telegram channel/chat {chat_id}...")
        with open(video_path, "rb") as vf:
            files = {
                "video": vf
            }
            data = {
                "chat_id": chat_id,
                "caption": caption[:1024], # Telegram captions are limited to 1024 chars unless premium
                "supports_streaming": "true"
            }
            res = requests.post(url, data=data, files=files, proxies=PROXIES, timeout=120)
            res.raise_for_status()
            res_data = res.json()
            
            if res_data.get("ok"):
                message_id = res_data.get("result", {}).get("message_id")
                post_url = f"https://t.me/{chat_id.replace('@', '')}/{message_id}" if chat_id.startswith("@") else "https://t.me/"
                logger.success(f"Successfully posted video to Telegram! Message ID: {message_id}")
                return {"message_id": message_id, "url": post_url}
                
            logger.error(f"Telegram sendVideo failed: {res_data}")
            return None
    except Exception as e:
        logger.error(f"Telegram upload failed: {e}")
        return None
