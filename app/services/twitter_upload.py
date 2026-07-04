import os
import json
import time
import requests
from typing import Optional
from requests_oauthlib import OAuth1
from loguru import logger
from app.config import config

CREDENTIALS_PATH = "twitter_credentials.json"
PROXIES = config.proxy

def load_twitter_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        return {}
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def check_twitter_credentials() -> str:
    creds = load_twitter_credentials()
    if not creds.get("consumer_key") or not creds.get("consumer_secret"):
        return "skipped-missing"
    if not creds.get("access_token") or not creds.get("access_token_secret"):
        return "skipped-missing"
        
    # Check validity via GET account verify_credentials
    url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    auth = OAuth1(
        creds["consumer_key"],
        creds["consumer_secret"],
        creds["access_token"],
        creds["access_token_secret"]
    )
    try:
        res = requests.get(url, auth=auth, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            return "ok"
        return "skipped-expired"
    except Exception as e:
        logger.error(f"Twitter credentials check error: {e}")
        return "skipped-expired"

def upload_to_twitter(video_path: str, caption: str) -> Optional[dict]:
    creds = load_twitter_credentials()
    consumer_key = creds.get("consumer_key")
    consumer_secret = creds.get("consumer_secret")
    access_token = creds.get("access_token")
    access_token_secret = creds.get("access_token_secret")
    
    if not consumer_key or not consumer_secret or not access_token or not access_token_secret:
        logger.error("Twitter upload failed: credentials missing.")
        return None
        
    if not os.path.exists(video_path):
        logger.error(f"Twitter upload failed: Video file not found: {video_path}")
        return None
        
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
    total_bytes = os.path.getsize(video_path)
    
    try:
        # Step 1: INIT
        logger.info("Initializing Twitter media upload (INIT)...")
        upload_url = "https://upload.twitter.com/1.1/media/upload.json"
        init_data = {
            "command": "INIT",
            "total_bytes": str(total_bytes),
            "media_type": "video/mp4",
            "media_category": "tweet_video"
        }
        res = requests.post(upload_url, auth=auth, data=init_data, proxies=PROXIES, timeout=30)
        res.raise_for_status()
        media_id = res.json()["media_id_string"]
        logger.info(f"Twitter media registered. ID: {media_id}")
        
        # Step 2: APPEND chunks
        logger.info("Uploading video payload to Twitter in chunks...")
        chunk_size = 1 * 1024 * 1024 # 1 MB chunks
        segment_index = 0
        
        with open(video_path, "rb") as vf:
            while True:
                chunk = vf.read(chunk_size)
                if not chunk:
                    break
                    
                append_data = {
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": str(segment_index)
                }
                append_files = {
                    "media": chunk
                }
                
                logger.info(f"Uploading chunk {segment_index} ({len(chunk)} bytes)...")
                append_res = requests.post(
                    upload_url,
                    auth=auth,
                    data=append_data,
                    files=append_files,
                    proxies=PROXIES,
                    timeout=60
                )
                append_res.raise_for_status()
                segment_index += 1
                
        # Step 3: FINALIZE
        logger.info("Finalizing Twitter media upload (FINALIZE)...")
        finalize_data = {
            "command": "FINALIZE",
            "media_id": media_id
        }
        finalize_res = requests.post(upload_url, auth=auth, data=finalize_data, proxies=PROXIES, timeout=30)
        finalize_res.raise_for_status()
        finalize_json = finalize_res.json()
        
        # Step 4: Poll STATUS (if asynchronous processing is needed)
        processing_info = finalize_json.get("processing_info")
        if processing_info:
            state = processing_info.get("state")
            while state in ["pending", "in_progress"]:
                check_after_secs = processing_info.get("check_after_secs", 5)
                logger.info(f"Twitter video processing state: {state}. Waiting {check_after_secs}s...")
                time.sleep(check_after_secs)
                
                status_params = {
                    "command": "STATUS",
                    "media_id": media_id
                }
                status_res = requests.get(upload_url, auth=auth, params=status_params, proxies=PROXIES, timeout=15)
                status_res.raise_for_status()
                status_json = status_res.json()
                
                processing_info = status_json.get("processing_info", {})
                state = processing_info.get("state")
                
                if state == "failed":
                    error_msg = processing_info.get("error", {}).get("message", "Unknown video processing error")
                    raise ValueError(f"Twitter video processing failed: {error_msg}")
                    
        logger.info("Twitter video upload processed and ready.")
        
        # Step 5: Post Tweet (v2 API)
        logger.info("Publishing Tweet to Twitter/X...")
        tweet_url = "https://api.twitter.com/2/tweets"
        tweet_payload = {
            "text": caption[:280], # Twitter limit
            "media": {
                "media_ids": [media_id]
            }
        }
        headers = {
            "Content-Type": "application/json"
        }
        tweet_res = requests.post(
            tweet_url,
            auth=auth,
            json=tweet_payload,
            headers=headers,
            proxies=PROXIES,
            timeout=30
        )
        tweet_res.raise_for_status()
        tweet_data = tweet_res.json()
        
        tweet_id = tweet_data.get("data", {}).get("id")
        if tweet_id:
            logger.success(f"Successfully posted video to Twitter/X! Tweet ID: {tweet_id}")
            post_url = f"https://x.com/user/status/{tweet_id}"
            return {"tweet_id": tweet_id, "url": post_url}
            
        logger.error(f"Twitter response missing tweet id: {tweet_data}")
        return None
        
    except Exception as e:
        logger.error(f"Twitter upload failed: {e}")
        return None
