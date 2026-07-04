import os
import json
import time
import requests
from typing import Optional
from loguru import logger
from app.config import config

CREDENTIALS_PATH = "tiktok_credentials.json"
PROXIES = config.proxy

def load_tiktok_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        return {}
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_tiktok_credentials(creds):
    try:
        with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save TikTok credentials: {e}")

def check_tiktok_credentials() -> str:
    creds = load_tiktok_credentials()
    if not creds.get("client_key") or not creds.get("client_secret"):
        return "skipped-missing"
    if not creds.get("access_token"):
        return "skipped-missing"
        
    url = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
    headers = {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    try:
        res = requests.post(url, headers=headers, json={}, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            return "ok"
        else:
            logger.warning(f"TikTok token invalid (status {res.status_code}). Attempting refresh...")
            if refresh_tiktok_token():
                return "refreshed"
            return "skipped-expired"
    except Exception as e:
        logger.error(f"TikTok credentials check error: {e}")
        return "skipped-expired"

def refresh_tiktok_token() -> bool:
    creds = load_tiktok_credentials()
    refresh_token = creds.get("refresh_token")
    client_key = creds.get("client_key")
    client_secret = creds.get("client_secret")
    
    if not refresh_token or not client_key or not client_secret:
        return False
        
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    try:
        res = requests.post(url, headers=headers, data=data, proxies=PROXIES, timeout=15)
        res.raise_for_status()
        res_data = res.json()
        
        access_token = res_data.get("access_token")
        new_refresh_token = res_data.get("refresh_token", refresh_token)
        
        if access_token:
            creds["access_token"] = access_token
            creds["refresh_token"] = new_refresh_token
            save_tiktok_credentials(creds)
            logger.info("Successfully refreshed TikTok access token.")
            return True
    except Exception as e:
        logger.error(f"Failed to refresh TikTok token: {e}")
        
    return False

def upload_to_tiktok(video_path: str, caption: str) -> Optional[dict]:
    logger.info("Attempting upload to TikTok via official API...")
    creds = load_tiktok_credentials()
    access_token = creds.get("access_token")
    api_success = False
    publish_id = None
    
    if access_token and os.path.exists(video_path):
        total_bytes = os.path.getsize(video_path)
        logger.info(f"Initializing TikTok video upload for file: {video_path} ({total_bytes} bytes)...")
        try:
            # Step 1: Initialize upload
            url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8"
            }
            payload = {
                "post_info": {
                    "title": caption[:2200],
                    "privacy_level": "SELF_ONLY",
                    "video_cover_timestamp_ms": 1000
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": total_bytes,
                    "chunk_size": total_bytes,
                    "total_chunk_count": 1
                }
            }
            res = requests.post(url, headers=headers, json=payload, proxies=PROXIES, timeout=30)
            res.raise_for_status()
            res_data = res.json()
            inner_data = res_data.get("data", {})
            publish_id = inner_data.get("publish_id")
            upload_url = inner_data.get("upload_url")
            
            if upload_url:
                # Step 2: Upload file binary directly via PUT
                logger.info("Pushing video payload binary to TikTok...")
                with open(video_path, "rb") as vf:
                    video_binary = vf.read()
                put_headers = {
                    "Content-Range": f"bytes 0-{total_bytes-1}/{total_bytes}",
                    "Content-Length": str(total_bytes),
                    "Content-Type": "video/mp4"
                }
                put_res = requests.put(upload_url, headers=put_headers, data=video_binary, proxies=PROXIES, timeout=300)
                put_res.raise_for_status()
                logger.success("Video payload uploaded successfully to TikTok via API.")
                api_success = True
        except Exception as api_err:
            logger.error(f"TikTok official API upload failed: {api_err}. Trying Playwright automation...")

    if api_success:
        if publish_id:
            return {"publish_id": publish_id, "url": "https://www.tiktok.com/"}
        return {"url": "https://www.tiktok.com/"}

    # ── Playwright Fallback ──
    logger.warning("Official TikTok API upload was not successful or is unaudited. Falling back to Playwright automation...")
    from app.services.tiktok_playwright import TT_COOKIES
    if not os.path.exists(TT_COOKIES):
        logger.error(f"[TikTok] Cookies missing at {TT_COOKIES}. Skipping background Playwright fallback. Please run 'python scratch/tiktok_login.py' manually first.")
        return None

    try:
        from app.services.tiktok_playwright import upload_to_tiktok_playwright
        res = upload_to_tiktok_playwright(video_path, caption)
        if res.get("success"):
            logger.success("TikTok upload completed successfully via Playwright fallback.")
            return {"url": res.get("url", "https://www.tiktok.com/")}
        else:
            logger.error(f"TikTok Playwright upload failed: {res.get('error')}")
    except Exception as pw_err:
        logger.error(f"TikTok Playwright fallback error: {pw_err}")
        
    return None
