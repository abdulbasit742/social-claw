import os
import json
import requests
from typing import Optional
from loguru import logger
from app.config import config

CREDENTIALS_PATH = "linkedin_credentials.json"
PROXIES = config.proxy
USERNAME = "shazil5506@gmail.com"
PASSWORD = "mouqeem273red"


def load_linkedin_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        return {}
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_linkedin_credentials(creds):
    try:
        with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save LinkedIn credentials: {e}")

def check_linkedin_credentials() -> str:
    creds = load_linkedin_credentials()
    
    # If we have email and password, or cookies, Playwright fallback will work
    if (creds.get("email") and creds.get("password")) or os.path.exists("linkedin_cookies.json") or (USERNAME and PASSWORD):
        return "ok"

    if not creds.get("client_id") or not creds.get("client_secret"):
        return "skipped-missing"
    if not creds.get("access_token") or not creds.get("person_urn"):
        return "skipped-missing"
        
    # Check validity via GET /me
    url = "https://api.linkedin.com/v2/me"
    headers = {
        "Authorization": f"Bearer {creds['access_token']}"
    }
    try:
        res = requests.get(url, headers=headers, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            return "ok"
        else:
            # Try to refresh
            logger.warning(f"LinkedIn token invalid (status {res.status_code}). Attempting refresh...")
            if refresh_linkedin_token():
                return "refreshed"
            return "skipped-expired"
    except Exception as e:
        logger.error(f"LinkedIn credentials check error: {e}")
        return "skipped-expired"


def refresh_linkedin_token() -> bool:
    creds = load_linkedin_credentials()
    refresh_token = creds.get("refresh_token")
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    
    if not refresh_token or not client_id or not client_secret:
        return False
        
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
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
            save_linkedin_credentials(creds)
            logger.info("Successfully refreshed LinkedIn access token.")
            return True
    except Exception as e:
        logger.error(f"Failed to refresh LinkedIn token: {e}")
        
    return False

def upload_to_linkedin(video_path: str = None, image_path: str = None, text: str = None) -> Optional[dict]:
    try:
        from app.services.linkedin_playwright import upload_to_linkedin_playwright
    except Exception as pe:
        logger.warning(f"Could not import linkedin_playwright: {pe}")
        upload_to_linkedin_playwright = None

    creds = load_linkedin_credentials()
    access_token = creds.get("access_token")
    person_urn = creds.get("person_urn")
    
    # If using Playwright (no access token or explicitly falling back for images/text)
    if not access_token or not person_urn or image_path or text:
        logger.warning("LinkedIn API token missing/unsupported for this format. Using Playwright automation fallback...")
        if upload_to_linkedin_playwright:
            res = upload_to_linkedin_playwright(video_path=video_path, image_path=image_path, text=text)
            if res and res.get("success"):
                return {"post_id": "playwright", "url": res.get("url")}
        return None
        
    if video_path and not os.path.exists(video_path):
        logger.error(f"LinkedIn upload failed: Video file not found: {video_path}")
        return None
        
    try:
        # Step 1: Register video upload asset
        logger.info("Registering video upload asset with LinkedIn...")
        register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                "owner": person_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        res = requests.post(register_url, headers=headers, json=payload, proxies=PROXIES, timeout=30)
        res.raise_for_status()
        res_data = res.json()
        
        value = res_data.get("value", {})
        asset_urn = value.get("asset")
        upload_mech = value.get("uploadMechanism", {})
        upload_http = upload_mech.get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
        upload_url = upload_http.get("uploadUrl")
        
        if not asset_urn or not upload_url:
            raise ValueError(f"Failed to parse registration response: {res_data}")
            
        # Step 2: Upload raw video binary
        logger.info("Uploading video payload to LinkedIn...")
        with open(video_path, "rb") as vf:
            video_binary = vf.read()
            
        put_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4"
        }
        
        put_res = requests.put(upload_url, headers=put_headers, data=video_binary, proxies=PROXIES, timeout=120)
        put_res.raise_for_status()
        logger.info("Video payload uploaded successfully to LinkedIn.")
        
        # Step 3: Create UGC Post share
        logger.info("Creating UGC Post share on LinkedIn feed...")
        ugc_url = "https://api.linkedin.com/v2/ugcPosts"
        ugc_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        ugc_payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "media": [
                        {
                            "media": asset_urn,
                            "status": "READY"
                        }
                    ],
                    "shareCommentary": {
                        "text": text or ""
                    },
                    "shareMediaCategory": "VIDEO"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        ugc_res = requests.post(ugc_url, headers=ugc_headers, json=ugc_payload, proxies=PROXIES, timeout=30)
        ugc_res.raise_for_status()
        ugc_data = ugc_res.json()
        
        post_id = ugc_data.get("id")
        if post_id:
            logger.success(f"Successfully posted video to LinkedIn! Post ID: {post_id}")
            # Construct a friendly post link
            feed_url = f"https://www.linkedin.com/feed/update/{post_id}"
            return {"post_id": post_id, "url": feed_url}
            
        logger.error(f"LinkedIn UGC post missing id: {ugc_data}")
        return None
    except Exception as e:
        logger.error(f"LinkedIn API upload failed: {e}. Trying Playwright fallback...")
        if upload_to_linkedin_playwright:
            res = upload_to_linkedin_playwright(video_path=video_path, image_path=image_path, text=text)
            if res and res.get("success"):
                return {"post_id": "playwright", "url": res.get("url")}
        return None

