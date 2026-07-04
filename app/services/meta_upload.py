import os
import time
import json
import shutil
import requests
from loguru import logger

# Proxy settings
PROXY_URL = "http://172.30.10.10:3128"
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

# Base directories
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_FILE = os.path.join(REPO_ROOT, "meta_credentials.json")
STATIC_DIR = os.path.join(REPO_ROOT, "webui", "static")

# Public Funnel base URL
FUNNEL_BASE_URL = "https://desktop-m52k54n.tail3983a9.ts.net/app/static"

def load_meta_credentials():
    """Loads Meta API credentials from meta_credentials.json."""
    if not os.path.exists(CREDENTIALS_FILE):
        return None

    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            creds = json.load(f)
            
        # Check for placeholder values
        placeholder_keys = [k for k, v in creds.items() if str(v).startswith("YOUR_")]
        if placeholder_keys:
            return None
            
        return creds
    except Exception as e:
        logger.error(f"Error loading Meta credentials: {e}")
        return None

def refresh_meta_token() -> bool:
    """Refreshes Meta access token by exchanging the current token for a long-lived one."""
    creds = load_meta_credentials()
    if not creds:
        return False
        
    app_id = creds.get("app_id")
    app_secret = creds.get("app_secret")
    token = creds.get("access_token")
    
    if not app_id or not app_secret or not token:
        return False
        
    logger.info("Attempting to refresh Meta long-lived access token...")
    url = "https://graph.facebook.com/v20.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": token
    }
    
    try:
        res = requests.get(url, params=params, proxies=PROXIES, timeout=30)
        res.raise_for_status()
        data = res.json()
        new_token = data.get("access_token")
        if new_token:
            creds["access_token"] = new_token
            with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
                json.dump(creds, f, ensure_ascii=False, indent=2)
            logger.success("Successfully refreshed and stored Meta access token.")
            return True
    except Exception as e:
        logger.warning(f"Failed to refresh Meta access token: {e}")
    return False

def check_meta_credentials() -> str:
    """
    Checks Meta credentials status.
    Returns: 'ok', 'skipped-missing', 'skipped-expired', 'refreshed'.
    """
    creds = load_meta_credentials()
    if not creds:
        return "skipped-missing"
        
    page_id = creds.get("page_id")
    ig_user_id = creds.get("instagram_business_account_id")
    access_token = creds.get("access_token")
    
    if not access_token or not page_id or not ig_user_id:
        return "skipped-missing"
        
    # Check validity via /me endpoint
    url = "https://graph.facebook.com/v20.0/me"
    params = {"access_token": access_token}
    try:
        res = requests.get(url, params=params, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            # Token is valid, try refreshing to extend validity
            refreshed = refresh_meta_token()
            return "refreshed" if refreshed else "ok"
        else:
            logger.warning(f"Meta token validation failed (status {res.status_code}): {res.text}")
            return "skipped-expired"
    except Exception as e:
        logger.warning(f"Meta credentials check failed: {e}")
        return "skipped-expired"

def upload_to_facebook(video_path: str, title: str, description: str) -> dict:
    """
    Uploads a video to the Facebook Page feed.
    Uses direct multipart file upload to graph-video.facebook.com with Playwright fallback.
    """
    try:
        from app.services.fb_playwright import upload_to_facebook_playwright
    except Exception as pe:
        logger.warning(f"Could not import fb_playwright: {pe}")
        upload_to_facebook_playwright = None

    creds = load_meta_credentials()
    if not creds or not creds.get("page_id") or not creds.get("access_token"):
        logger.warning("Facebook API credentials missing or incomplete. Attempting Playwright fallback...")
        if upload_to_facebook_playwright:
            res = upload_to_facebook_playwright(video_path, description)
            if res and res.get("success"):
                return {"id": "playwright", "url": res.get("url")}
        return None

    page_id = creds.get("page_id")
    access_token = creds.get("access_token")
    url = f"https://graph-video.facebook.com/v20.0/{page_id}/videos"
    
    logger.info(f"Uploading video '{title}' to Facebook Page {page_id}...")
    
    payload = {
        "access_token": access_token,
        "title": title,
        "description": description
    }

    try:
        with open(video_path, "rb") as video_file:
            files = {
                "source": (os.path.basename(video_path), video_file, "video/mp4")
            }
            
            response = requests.post(url, data=payload, files=files, proxies=PROXIES, timeout=300)
            response.raise_for_status()
            res_data = response.json()
            video_id = res_data.get("id")
            
            if not video_id:
                raise ValueError(f"No video ID returned from Facebook API: {res_data}")

            post_url = f"https://www.facebook.com/{video_id}"
            logger.success(f"Successfully posted video to Facebook Page! ID: {video_id}, URL: {post_url}")
            return {"id": video_id, "url": post_url}
            
    except Exception as e:
        logger.error(f"Facebook Graph API upload failed: {e}. Trying Playwright fallback...")
        if upload_to_facebook_playwright:
            res = upload_to_facebook_playwright(video_path, description)
            if res and res.get("success"):
                return {"id": "playwright", "url": res.get("url")}
        raise e


def upload_to_instagram(video_path: str, caption: str) -> dict:
    """
    Uploads a video to Instagram Reels.
    Attempts direct upload via instagrapi first if personal credentials exist.
    Exposes the file through the local Streamlit static folder via Tailscale Funnel as fallback.
    Uses the Meta Graph API create-container -> poll -> publish flow.
    """
    # Check for direct instagrapi bypass credentials
    personal_creds_file = os.path.join(REPO_ROOT, "instagram_personal.json")
    if os.path.exists(personal_creds_file):
        try:
            logger.info("Found Instagram personal credentials. Attempting direct Reels upload via instagrapi...")
            with open(personal_creds_file, "r", encoding="utf-8") as pf:
                p_creds = json.load(pf)
            username = p_creds.get("username")
            password = p_creds.get("password")
            if username and password:
                from instagrapi import Client
                cl = Client()
                cl.set_proxy(PROXY_URL)
                logger.info(f"Logging in to Instagram as {username}...")
                cl.login(username, password)
                logger.info("Instagram login successful. Posting Reels media payload...")
                # instagrapi expects vertical video.
                media = cl.clip_upload(video_path, caption)
                reel_url = f"https://www.instagram.com/reel/{media.code}/"
                logger.success(f"Successfully posted Reel directly to Instagram via instagrapi! URL: {reel_url}")
                return {"id": media.id, "url": reel_url}
        except Exception as inst_err:
            logger.warning(f"instagrapi direct upload failed: {inst_err}. Falling back to official Meta Graph API...")

    creds = load_meta_credentials()
    if not creds:
        logger.warning("Instagram upload skipped: Credentials missing or incomplete.")
        return None

    ig_user_id = creds.get("instagram_business_account_id")
    access_token = creds.get("access_token")

    if not ig_user_id or not access_token:
        logger.warning("Instagram upload skipped: instagram_business_account_id or access_token missing.")
        return None

    # Step 1: Copy video to static directory to make it publicly accessible via Funnel (as fallback)
    os.makedirs(STATIC_DIR, exist_ok=True)
    temp_filename = f"ig_temp_{int(time.time())}.mp4"
    temp_path = os.path.join(STATIC_DIR, temp_filename)
    
    logger.info(f"Copying video to static path {temp_path} for public accessibility...")
    shutil.copy2(video_path, temp_path)
    
    public_url = f"{FUNNEL_BASE_URL}/{temp_filename}"
    
    # Try uploading to tmpfiles.org to get a direct public URL (bypassing local Tailscale Funnel offline states)
    try:
        logger.info("Uploading video to tmpfiles.org to get public URL for Instagram...")
        with open(video_path, "rb") as f:
            t_res = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                proxies=PROXIES,
                timeout=120
            )
        t_res.raise_for_status()
        res_data = t_res.json()
        raw_url = res_data.get("data", {}).get("url")
        if raw_url:
            # Convert to direct download link
            public_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            logger.info(f"Instagram video temporary public URL (tmpfiles.org): {public_url}")
        else:
            raise ValueError("No URL returned in tmpfiles.org response")
    except Exception as e:
        logger.warning(f"tmpfiles.org upload failed: {e}. Falling back to Tailscale Funnel URL: {public_url}")

    try:
        # Step 2: Create media container
        container_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media"
        container_payload = {
            "media_type": "REELS",
            "video_url": public_url,
            "caption": caption,
            "access_token": access_token
        }
        
        logger.info("Initializing Instagram media container creation...")
        res = requests.post(container_url, data=container_payload, proxies=PROXIES, timeout=60)
        if res.status_code != 200:
            logger.error(f"Instagram media container failed. Status: {res.status_code}, Body: {res.text}")
        res.raise_for_status()
        container_id = res.json().get("id")
        
        if not container_id:
            raise ValueError(f"Failed to get container ID from Instagram: {res.text}")
            
        logger.info(f"Instagram media container created. ID: {container_id}. Polling status...")

        # Step 3: Poll status
        start_time = time.time()
        status_url = f"https://graph.facebook.com/v20.0/{container_id}"
        status_params = {
            "fields": "status_code,status",
            "access_token": access_token
        }
        
        # Poll for up to 5 minutes
        while time.time() - start_time < 300:
            time.sleep(15)
            status_res = requests.get(status_url, params=status_params, proxies=PROXIES, timeout=30)
            status_res.raise_for_status()
            status_data = status_res.json()
            
            status_code = status_data.get("status_code")
            status_text = status_data.get("status")
            
            logger.info(f"Container status: {status_code} ({status_text})")
            
            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                raise ValueError(f"Instagram container encoding failed: {status_data}")
        else:
            raise TimeoutError("Timed out waiting for Instagram media container to finish encoding.")

        # Step 4: Publish Reel
        publish_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish"
        publish_payload = {
            "creation_id": container_id,
            "access_token": access_token
        }
        
        logger.info(f"Publishing Reels container {container_id}...")
        pub_res = requests.post(publish_url, data=publish_payload, proxies=PROXIES, timeout=60)
        pub_res.raise_for_status()
        media_id = pub_res.json().get("id")
        
        if not media_id:
            raise ValueError(f"Failed to get media ID from Instagram publish response: {pub_res.text}")

        # Step 5: Get permalink
        permalink = f"https://www.instagram.com/p/{media_id}/"
        try:
            info_url = f"https://graph.facebook.com/v20.0/{media_id}"
            info_params = {
                "fields": "permalink",
                "access_token": access_token
            }
            info_res = requests.get(info_url, params=info_params, proxies=PROXIES, timeout=30)
            if info_res.ok:
                permalink = info_res.json().get("permalink", permalink)
        except Exception as info_err:
            logger.warning(f"Could not retrieve exact Instagram permalink: {info_err}")

        logger.success(f"Successfully published Reel to Instagram! ID: {media_id}, URL: {permalink}")
        return {"id": media_id, "url": permalink}
    except Exception as e:
        logger.error(f"Instagram Graph API upload failed: {e}. Trying Playwright fallback...")
        try:
            from app.services.instagram_playwright import upload_to_instagram_playwright
            res = upload_to_instagram_playwright(video_path, caption)
            if res.get("success"):
                logger.success("Successfully posted Reel to Instagram via Playwright!")
                return {"id": "playwright", "url": "https://www.instagram.com/", "method": "playwright"}
            else:
                logger.error(f"Instagram Playwright fallback failed: {res.get('error')}")
                raise e
        except Exception as pw_err:
            logger.error(f"Instagram Playwright import/run error: {pw_err}")
            raise e
    finally:
        # Step 6: Clean up the exposed public file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Removed temporary video from static path: {temp_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to delete temporary video file {temp_path}: {cleanup_err}")

def upload_image_to_facebook(image_path: str, caption: str) -> dict:
    """
    Uploads a photo/image to the Facebook Page feed.
    Uses direct Graph API POST to /{page_id}/photos.
    """
    creds = load_meta_credentials()
    if not creds or not creds.get("page_id") or not creds.get("access_token"):
        logger.warning("Facebook API credentials missing or incomplete. Skipping Graph API image upload.")
        return None

    page_id = creds.get("page_id")
    access_token = creds.get("access_token")
    url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
    
    logger.info(f"Uploading image to Facebook Page {page_id}...")
    
    payload = {
        "access_token": access_token,
        "caption": caption
    }

    try:
        with open(image_path, "rb") as image_file:
            files = {
                "source": (os.path.basename(image_path), image_file, "image/jpeg")
            }
            response = requests.post(url, data=payload, files=files, proxies=PROXIES, timeout=120)
            response.raise_for_status()
            res_data = response.json()
            photo_id = res_data.get("id")
            
            if not photo_id:
                raise ValueError(f"No photo ID returned from Facebook API: {res_data}")

            post_url = f"https://www.facebook.com/{photo_id}"
            logger.success(f"Successfully posted image to Facebook Page! ID: {photo_id}, URL: {post_url}")
            return {"id": photo_id, "url": post_url}
    except Exception as e:
        logger.error(f"Facebook Graph API image upload failed: {e}")
        raise e

def upload_image_to_instagram(image_path: str, caption: str) -> dict:
    """
    Uploads a photo/image to Instagram feed.
    Attempts direct upload via instagrapi first if personal credentials exist.
    Uses official Graph API media/publish flow.
    """
    # Check for direct instagrapi bypass credentials
    personal_creds_file = os.path.join(REPO_ROOT, "instagram_personal.json")
    if os.path.exists(personal_creds_file):
        try:
            logger.info("Found Instagram personal credentials. Attempting direct image upload via instagrapi...")
            with open(personal_creds_file, "r", encoding="utf-8") as pf:
                p_creds = json.load(pf)
            username = p_creds.get("username")
            password = p_creds.get("password")
            if username and password:
                from instagrapi import Client
                cl = Client()
                cl.set_proxy(PROXY_URL)
                logger.info(f"Logging in to Instagram as {username}...")
                cl.login(username, password)
                logger.info("Instagram login successful. Posting photo media payload...")
                media = cl.photo_upload(image_path, caption)
                photo_url = f"https://www.instagram.com/p/{media.code}/"
                logger.success(f"Successfully posted image directly to Instagram via instagrapi! URL: {photo_url}")
                return {"id": media.id, "url": photo_url}
        except Exception as inst_err:
            logger.warning(f"instagrapi direct image upload failed: {inst_err}. Falling back to official Meta Graph API...")

    creds = load_meta_credentials()
    if not creds:
        logger.warning("Instagram image upload skipped: Credentials missing or incomplete.")
        return None

    ig_user_id = creds.get("instagram_business_account_id")
    access_token = creds.get("access_token")

    if not ig_user_id or not access_token:
        logger.warning("Instagram image upload skipped: instagram_business_account_id or access_token missing.")
        return None

    # Step 1: Upload image to tmpfiles.org to get a direct public URL
    public_url = None
    try:
        logger.info("Uploading image to tmpfiles.org to get public URL for Instagram...")
        with open(image_path, "rb") as f:
            t_res = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                proxies=PROXIES,
                timeout=60
            )
        t_res.raise_for_status()
        res_data = t_res.json()
        raw_url = res_data.get("data", {}).get("url")
        if raw_url:
            public_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            logger.info(f"Instagram image temporary public URL: {public_url}")
        else:
            raise ValueError("No URL returned in tmpfiles.org response")
    except Exception as e:
        logger.error(f"tmpfiles.org image upload failed: {e}")
        return None

    try:
        # Step 2: Create media container for image
        container_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media"
        container_payload = {
            "image_url": public_url,
            "caption": caption,
            "access_token": access_token
        }
        
        logger.info("Initializing Instagram image container creation...")
        res = requests.post(container_url, data=container_payload, proxies=PROXIES, timeout=60)
        res.raise_for_status()
        container_id = res.json().get("id")
        
        if not container_id:
            raise ValueError(f"Failed to get container ID from Instagram: {res.text}")
            
        logger.info(f"Instagram image container created. ID: {container_id}. Publishing...")

        # Step 3: Publish Image
        publish_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish"
        publish_payload = {
            "creation_id": container_id,
            "access_token": access_token
        }
        
        publish_res = requests.post(publish_url, data=publish_payload, proxies=PROXIES, timeout=60)
        publish_res.raise_for_status()
        media_id = publish_res.json().get("id")
        
        if media_id:
            ig_post_url = f"https://www.instagram.com/p/{media_id}"
            logger.success(f"Successfully posted image to Instagram! ID: {media_id}, URL: {ig_post_url}")
            return {"id": media_id, "url": ig_post_url}
    except Exception as e:
        logger.error(f"Instagram Graph API image upload failed: {e}")
        raise e


def upload_text_to_facebook(message: str) -> dict:
    """
    Uploads a text-only status update to the Facebook Page feed.
    Uses direct Graph API POST to /{page_id}/feed.
    """
    creds = load_meta_credentials()
    if not creds or not creds.get("page_id") or not creds.get("access_token"):
        logger.warning("Facebook API credentials missing or incomplete. Skipping text upload.")
        return None

    page_id = creds.get("page_id")
    access_token = creds.get("access_token")
    url = f"https://graph.facebook.com/v20.0/{page_id}/feed"
    
    logger.info(f"Posting text update to Facebook Page {page_id}...")
    
    payload = {
        "access_token": access_token,
        "message": message
    }

    try:
        response = requests.post(url, data=payload, proxies=PROXIES, timeout=60)
        response.raise_for_status()
        res_data = response.json()
        post_id = res_data.get("id")
        
        if not post_id:
            raise ValueError(f"No post ID returned from Facebook API: {res_data}")

        post_url = f"https://www.facebook.com/{post_id}"
        logger.success(f"Successfully posted text update to Facebook Page! ID: {post_id}, URL: {post_url}")
        return {"id": post_id, "url": post_url}
    except Exception as e:
        logger.error(f"Facebook Graph API text post failed: {e}")
        raise e
