import os
import sys
import json
import time
import logging
import urllib.request
import subprocess
from datetime import datetime

# Configure Python path to import app modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Force stdout to UTF-8 on Windows to prevent cp1252 logging crash
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Enforce environment variables defensively
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/auto_factory.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# File Paths
CONFIG_PATH = "auto_factory.config.json"
TOPICS_PATH = "scripts/topics.json"
DONE_PATH = "scripts/done.json"

def load_config():
    default_config = {
        "niche": "fascinating history & psychology facts",
        "videos_per_day": 5,
        "privacy": "unlisted",
        "daily_run_time": "02:00",
        "post_youtube": True,
        "post_facebook": True,
        "post_instagram": True,
        "use_ai_clips": False
    }
    if not os.path.exists(CONFIG_PATH):
        return default_config
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            # Merge with defaults
            default_config.update(user_config)
            return default_config
    except Exception as e:
        logging.error(f"Failed to load config, using defaults: {e}")
        return default_config

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load {path}, returning empty dict: {e}")
        return {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Failed to save {path}: {e}")

def call_ollama(prompt, json_mode=False):
    url = "http://127.0.0.1:11434/api/generate"
    data = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }
    if json_mode:
        data["format"] = "json"
        
    req_data = json.dumps(data).encode("utf-8")
    proxy_support = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_support)
    
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    # Retry logic
    for i in range(3):
        try:
            with opener.open(req, timeout=180) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                return resp_data.get("response", "").strip()
        except Exception as e:
            logging.warning(f"Ollama connection attempt {i+1} failed: {e}")
            if i < 2:
                time.sleep(5)
    raise ConnectionError("Failed to reach Ollama qwen2.5:7b after 3 attempts.")

def brainstorm_topics(niche, done_log):
    logging.info(f"Brainstorming fresh topics for niche '{niche}'...")
    done_topics = list(done_log.keys())
    
    prompt = (
        f"You are a brainstorm assistant. Niche: '{niche}'. "
        f"Brainstorm 20 fresh, distinct and highly engaging short-video topics (under 10 words each). "
        f"These topics must NOT be in this list: {done_topics}. "
        f"Return ONLY a JSON object containing a 'topics' list of strings, e.g.: "
        f"{{\"topics\": [\"Topic 1\", \"Topic 2\", ...]}}"
    )
    
    try:
        res = call_ollama(prompt, json_mode=True)
        parsed = json.loads(res)
        topics = parsed.get("topics", [])
        logging.info(f"Successfully brainstormed {len(topics)} new topics.")
        return topics
    except Exception as e:
        logging.error(f"Failed to brainstorm topics: {e}")
        return []

def generate_script(topic, niche):
    logging.info(f"Generating script for topic '{topic}'...")
    prompt = (
        f"Write a highly engaging, confident, and punchy short-form video script (e.g. for YouTube Shorts / TikTok) about the topic: '{topic}' in the niche: '{niche}'.\n"
        f"Word count constraint: MUST be strictly between 150 and 170 words (essential for short-form pacing).\n\n"
        f"Formatting constraints:\n"
        f"- Do NOT write any narrator instructions, sound effect labels, stage directions, scene headings, or headers. Output ONLY the spoken words.\n"
        f"- Use short, punchy sentences and dramatic ellipses (...) to make the speech feel natural and professional.\n\n"
        f"Structure your script exactly as follows:\n"
        f"1. Hook: Start with a strong, curiosity-driven hook in the first line that instantly grabs attention.\n"
        f"2. Lesson/Insight: Present one punchy, memorable business lesson or real-world startup story.\n"
        f"3. Takeaway: Provide a clear, practical step the viewer can act on today.\n"
        f"4. Closing: End with a highly motivating call to action (e.g., 'If you want to win in business, follow for daily startup strategies!')."
    )
    try:
        script = call_ollama(prompt, json_mode=False)
        word_count = len(script.split())
        logging.info(f"Generated script of {word_count} words.")
        return script
    except Exception as e:
        logging.error(f"Failed to generate script: {e}")
        return None

def print_youtube_instructions():
    print("""
======================================================================
                     YOUTUBE OAUTH CREDENTIALS SETUP
======================================================================
1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select an existing one.
3. Enable the "YouTube Data API v3" for your project.
4. Go to the "OAuth consent screen" page:
   - Choose User Type: "External" (or "Internal" if you have Google Workspace).
   - Fill in the App name, User support email, and Developer contact information.
   - Click "Save and Continue".
   - Under "Scopes", add ".../auth/youtube.upload".
   - Under "Test users", add your own Google Account/YouTube Channel email.
5. Go to the "Credentials" page:
   - Click "+ CREATE CREDENTIALS" and choose "OAuth client ID".
   - Select Application type: "Desktop app".
   - Name your client and click "Create".
6. Download the JSON credentials file.
7. Rename the downloaded file to 'client_secret.json' and place it in the project root:
   C:\\Users\\absh5\\MoneyPrinterTurbo\\client_secret.json
======================================================================
""")

def print_meta_instructions():
    print("""
======================================================================
                     META (FACEBOOK/INSTAGRAM) CREDENTIALS SETUP
======================================================================
1. Go to the Meta Developers Console: https://developers.facebook.com/
2. Create a new Developer App (select "Other" -> "Business" or similar type).
3. Under App Dashboard, copy the App ID and App Secret.
4. Go to the Graph API Explorer tool:
   https://developers.facebook.com/tools/explorer/
   - Select your App from the dropdown.
   - Click "Generate Access Token" and approve permissions:
     pages_manage_posts, pages_read_engagement, instagram_basic, instagram_content_publish
5. Retrieve your Facebook Page ID and Instagram Business Account ID:
   - You can get these via the Graph API Explorer by querying:
     GET: /me/accounts  (to get Page IDs and Page tokens)
     GET: /{page_id}?fields=instagram_business_account  (to get IG ID)
6. To convert your short-lived access token into a long-lived Page token,
   paste the parameters into C:\\Users\\absh5\\MoneyPrinterTurbo\\meta_credentials.json:
   {
     "app_id": "<app_id>",
     "app_secret": "<app_secret>",
     "page_id": "<page_id>",
     "instagram_business_account_id": "<instagram_business_account_id>",
     "access_token": "<generated_token>"
   }
======================================================================
""")

def print_tiktok_instructions():
    print("""
======================================================================
                     TIKTOK DEVELOPER APP SETUP
======================================================================
1. Go to the TikTok Developer Portal: https://developers.tiktok.com/
2. Register and create a new App under "My Apps".
3. Under "Products", add the "Content Posting API".
4. Copy your Client Key and Client Secret.
5. Perform the OAuth flow to get your Access Token and Refresh Token.
6. Create 'tiktok_credentials.json' in the project root:
   {
     "client_key": "<client_key>",
     "client_secret": "<client_secret>",
     "access_token": "<access_token>",
     "refresh_token": "<refresh_token>"
   }
======================================================================
""")

def print_linkedin_instructions():
    print("""
======================================================================
                     LINKEDIN DEVELOPER APP SETUP
======================================================================
1. Go to the LinkedIn Developer Portal: https://developer.linkedin.com/
2. Create an App, link to your Page/Company, and add "Share on LinkedIn".
3. Copy your Client ID and Client Secret from "Auth".
4. Generate a 3-legged access token with the 'w_member_social' scope.
5. Get your URN by querying GET https://api.linkedin.com/v2/me.
6. Create 'linkedin_credentials.json' in the project root:
   {
     "client_id": "<client_id>",
     "client_secret": "<client_secret>",
     "access_token": "<access_token>",
     "refresh_token": "<refresh_token>",
     "person_urn": "urn:li:person:<id>"
   }
======================================================================
""")

def print_telegram_instructions():
    print("""
======================================================================
                     TELEGRAM BOT CREDENTIALS SETUP
======================================================================
1. Open Telegram and search for '@BotFather'.
2. Send /newbot and follow instructions to get your Bot Token.
3. Create a Telegram Channel and make your bot an Administrator.
4. Copy your channel username or chat ID.
5. Create 'telegram_credentials.json' in the project root:
   {
     "bot_token": "<bot_token>",
     "chat_id": "<chat_id_or_channel_username>"
   }
======================================================================
""")

def print_twitter_instructions():
    print("""
======================================================================
                     TWITTER/X DEVELOPER APP SETUP
======================================================================
1. Go to the X Developer Portal: https://developer.x.com/
2. Sign up, create a Project and an App.
3. In App Settings -> User Authentication Settings:
   - Enable OAuth 1.0a.
   - Set App Permissions to "Read and Write".
   - Set Type to "Web App, Automated App or Bot".
4. Go to Keys and Tokens:
   - Copy Consumer Keys: API Key and API Secret.
   - Copy Authentication Tokens: Access Token and Access Token Secret (Read/Write).
5. Create 'twitter_credentials.json' in the project root:
   {
     "consumer_key": "<api_key>",
     "consumer_secret": "<api_secret>",
     "access_token": "<access_token>",
     "access_token_secret": "<access_token_secret>"
   }
======================================================================
""")

def check_youtube_credentials() -> str:
    """Checks YouTube credentials status. Returns 'ok', 'skipped-missing', 'skipped-expired', 'refreshed'."""
    client_secrets_file = "client_secret.json"
    token_file = "youtube_token.json"
    
    if not os.path.exists(client_secrets_file):
        return "skipped-missing"
    if not os.path.exists(token_file):
        return "skipped-missing"
        
    try:
        import google.oauth2.credentials
        from google.auth.transport.requests import Request
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
            token_file, 
            ['https://www.googleapis.com/auth/youtube.upload']
        )
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                logger = logging.getLogger()
                logger.info("Refreshing expired YouTube OAuth credentials...")
                creds.refresh(Request())
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())
                return "refreshed"
            else:
                return "skipped-expired"
        return "ok"
    except Exception as e:
        logging.warning(f"YouTube credentials check failed: {e}")
        return "skipped-expired"

def count_today_uploads(done_log):
    today_str = datetime.now().strftime("%Y-%m-%d")
    count = 0
    for details in done_log.values():
        if details.get("date") == today_str:
            yt = details.get("youtube_url")
            fb = details.get("facebook_url")
            ig = details.get("instagram_url")
            tk = details.get("tiktok_url")
            li = details.get("linkedin_url")
            tg = details.get("telegram_url")
            tw = details.get("twitter_url")
            
            has_yt = yt and yt != "local-only"
            has_fb = fb and fb != "local-only"
            has_ig = ig and ig != "local-only"
            has_tk = tk and tk != "local-only"
            has_li = li and li != "local-only"
            has_tg = tg and tg != "local-only"
            has_tw = tw and tw != "local-only"
            
            if has_yt or has_fb or has_ig or has_tk or has_li or has_tg or has_tw:
                count += 1
    return count

def trigger_post_engagement(config, topic, urls_data):
    # Pin first comment if enabled
    if config.get("enable_first_comment", False):
        try:
            logging.info(f"Triggering first comment pinning for '{topic}'...")
            from app.services.engagement import run_engagement_loop
            run_engagement_loop(topic, {
                "youtube": urls_data.get("youtube_url"),
                "facebook": urls_data.get("facebook_url"),
                "instagram": urls_data.get("instagram_url"),
                "linkedin": urls_data.get("linkedin_url")
            })
        except Exception as e:
            logging.error(f"Failed to pin first comment: {e}")
            
    # Auto-reply to recent comments if enabled
    if config.get("enable_auto_reply", False):
        try:
            logging.info("Triggering auto-reply scan for recent comments...")
            from app.services.engagement import auto_reply_to_recent_comments
            max_rep = int(config.get("max_replies_per_post_run", 5))
            auto_reply_to_recent_comments(max_rep)
        except Exception as e:
            logging.error(f"Failed to auto-reply to comments: {e}")

def main():
    logging.info("========================================")
    logging.info("Starting Autonomous Multi-Format Factory...")
    
    config = load_config()
    niche = config["niche"]
    videos_per_day = min(int(config.get("posts_per_day", config.get("videos_per_day", 500))), 500) # Safety cap
    privacy = config["privacy"]
    
    post_youtube = config.get("post_youtube", True)
    
    post_facebook_video = config.get("post_facebook_video", config.get("post_facebook", True))
    post_facebook_image = config.get("post_facebook_image", config.get("post_facebook", True))
    post_facebook_text = config.get("post_facebook_text", config.get("post_facebook", True))
    post_facebook = post_facebook_video or post_facebook_image or post_facebook_text
    
    post_instagram_video = config.get("post_instagram_video", config.get("post_instagram", True))
    post_instagram_image = config.get("post_instagram_image", config.get("post_instagram", True))
    post_instagram = post_instagram_video or post_instagram_image
    
    post_linkedin_video = config.get("post_linkedin_video", config.get("post_linkedin", False))
    post_linkedin_image = config.get("post_linkedin_image", config.get("post_linkedin", False))
    post_linkedin_text = config.get("post_linkedin_text", config.get("post_linkedin", False))
    post_linkedin = post_linkedin_video or post_linkedin_image or post_linkedin_text
    
    post_tiktok = config.get("post_tiktok", False)
    post_telegram = config.get("post_telegram", False)
    post_twitter = config.get("post_twitter", False)
    
    ratio_video_vs_image = float(config.get("ratio_video_vs_image", 0.5))
    
    logging.info(f"Niche: {niche}")
    logging.info(f"Daily Cap: {videos_per_day}")
    logging.info(f"Privacy: {privacy}")
    logging.info(f"Video vs Image Ratio: {ratio_video_vs_image}")
    logging.info(f"Post YouTube: {post_youtube}")
    logging.info(f"Post FB (Video/Image/Text): {post_facebook_video}/{post_facebook_image}/{post_facebook_text}")
    logging.info(f"Post IG (Video/Image): {post_instagram_video}/{post_instagram_image}")
    logging.info(f"Post LinkedIn (Video/Image/Text): {post_linkedin_video}/{post_linkedin_image}/{post_linkedin_text}")
    logging.info(f"Post TikTok: {post_tiktok}")
    logging.info(f"Post Telegram: {post_telegram}")
    logging.info(f"Post Twitter: {post_twitter}")

    # Track original settings
    post_youtube_orig = post_youtube
    post_facebook_video_orig = post_facebook_video
    post_facebook_image_orig = post_facebook_image
    post_facebook_text_orig = post_facebook_text
    post_instagram_video_orig = post_instagram_video
    post_instagram_image_orig = post_instagram_image
    post_linkedin_video_orig = post_linkedin_video
    post_linkedin_image_orig = post_linkedin_image
    post_linkedin_text_orig = post_linkedin_text
    post_tiktok_orig = post_tiktok
    post_telegram_orig = post_telegram
    post_twitter_orig = post_twitter

    # Check credentials on startup
    yt_status = "ok"
    if post_youtube:
        yt_status = check_youtube_credentials()
        logging.info(f"YouTube credentials status: {yt_status}")
        if yt_status == "skipped-missing":
            print_youtube_instructions()
            logging.info("Waiting 15s for client_secret.json / youtube_token.json to be created...")
            time.sleep(15)
            yt_status = check_youtube_credentials()
            if yt_status == "skipped-missing":
                logging.warning("YouTube credentials still missing. Skipping YouTube upload for this run.")
                post_youtube = False
        elif yt_status == "skipped-expired":
            logging.warning("YouTube credentials expired or invalid. Skipping YouTube upload for this run.")
            post_youtube = False

    meta_status = "ok"
    if post_facebook or post_instagram:
        from app.services import meta_upload
        meta_status = meta_upload.check_meta_credentials()
        logging.info(f"Meta credentials status: {meta_status}")
        if meta_status == "skipped-missing":
            print_meta_instructions()
            logging.info("Waiting 15s for meta_credentials.json to be created...")
            time.sleep(15)
            meta_status = meta_upload.check_meta_credentials()
            if meta_status == "skipped-missing":
                logging.warning("Meta credentials still missing. Skipping Facebook and Instagram upload for this run.")
                if post_facebook:
                    post_facebook = False
                    post_facebook_video = False
                    post_facebook_image = False
                    post_facebook_text = False
                if post_instagram:
                    post_instagram = False
                    post_instagram_video = False
                    post_instagram_image = False
        elif meta_status == "skipped-expired":
            logging.warning("Meta credentials expired or invalid. Skipping Facebook and Instagram upload for this run.")
            if post_facebook:
                post_facebook = False
                post_facebook_video = False
                post_facebook_image = False
                post_facebook_text = False
            if post_instagram:
                post_instagram = False
                post_instagram_video = False
                post_instagram_image = False
    
    tiktok_status = "ok"
    if post_tiktok:
        from app.services import tiktok_upload
        tiktok_status = tiktok_upload.check_tiktok_credentials()
        logging.info(f"TikTok credentials status: {tiktok_status}")
        if tiktok_status == "skipped-missing":
            print_tiktok_instructions()
            logging.info("Waiting 15s for tiktok_credentials.json to be created...")
            time.sleep(15)
            tiktok_status = tiktok_upload.check_tiktok_credentials()
            if tiktok_status == "skipped-missing":
                logging.warning("TikTok credentials still missing. Skipping TikTok upload for this run.")
                post_tiktok = False
        elif tiktok_status == "skipped-expired":
            logging.warning("TikTok credentials expired or invalid. Skipping TikTok upload for this run.")
            post_tiktok = False

    linkedin_status = "ok"
    if post_linkedin:
        from app.services import linkedin_upload
        linkedin_status = linkedin_upload.check_linkedin_credentials()
        logging.info(f"LinkedIn credentials status: {linkedin_status}")
        if linkedin_status == "skipped-missing":
            print_linkedin_instructions()
            logging.info("Waiting 15s for linkedin_credentials.json to be created...")
            time.sleep(15)
            linkedin_status = linkedin_upload.check_linkedin_credentials()
            if linkedin_status == "skipped-missing":
                logging.warning("LinkedIn credentials still missing. Skipping LinkedIn upload for this run.")
                if post_linkedin:
                    post_linkedin = False
                    post_linkedin_video = False
                    post_linkedin_image = False
                    post_linkedin_text = False
        elif linkedin_status == "skipped-expired":
            logging.warning("LinkedIn credentials expired or invalid. Skipping LinkedIn upload for this run.")
            if post_linkedin:
                post_linkedin = False
                post_linkedin_video = False
                post_linkedin_image = False
                post_linkedin_text = False

    telegram_status = "ok"
    if post_telegram:
        from app.services import telegram_upload
        telegram_status = telegram_upload.check_telegram_credentials()
        logging.info(f"Telegram credentials status: {telegram_status}")
        if telegram_status == "skipped-missing":
            print_telegram_instructions()
            logging.info("Waiting 15s for telegram_credentials.json to be created...")
            time.sleep(15)
            telegram_status = telegram_upload.check_telegram_credentials()
            if telegram_status == "skipped-missing":
                logging.warning("Telegram credentials still missing. Skipping Telegram upload for this run.")
                post_telegram = False
        elif telegram_status == "skipped-expired":
            logging.warning("Telegram credentials expired or invalid. Skipping Telegram upload for this run.")
            post_telegram = False

    twitter_status = "ok"
    if post_twitter:
        from app.services import twitter_upload
        twitter_status = twitter_upload.check_twitter_credentials()
        logging.info(f"Twitter credentials status: {twitter_status}")
        if twitter_status == "skipped-missing":
            print_twitter_instructions()
            logging.info("Waiting 15s for twitter_credentials.json to be created...")
            time.sleep(15)
            twitter_status = twitter_upload.check_twitter_credentials()
            if twitter_status == "skipped-missing":
                logging.warning("Twitter credentials still missing. Skipping Twitter upload for this run.")
                post_twitter = False
        elif twitter_status == "skipped-expired":
            logging.warning("Twitter credentials expired or invalid. Skipping Twitter upload for this run.")
            post_twitter = False

    # Load queues
    done_log = load_json(DONE_PATH)
    topics_queue = load_json(TOPICS_PATH).get("queue", [])
    
    # Quota check
    today_uploads = count_today_uploads(done_log)
    logging.info(f"Uploaded today: {today_uploads}/{videos_per_day}")

    # Catch-up for offline local-only videos
    catchup_count = 0
    # Bypassed to start new parallel GPU video generations immediately
    for topic, entry in []:
        video_path = entry.get("local_video_path")
        if not video_path or not os.path.exists(video_path):
            continue
            
        needs_yt = post_youtube and entry.get("youtube_url") == "local-only"
        needs_fb = post_facebook and entry.get("facebook_url") == "local-only"
        needs_ig = post_instagram and entry.get("instagram_url") == "local-only"
        needs_tk = post_tiktok and entry.get("tiktok_url") == "local-only"
        needs_li = post_linkedin and entry.get("linkedin_url") == "local-only"
        needs_tg = post_telegram and entry.get("telegram_url") == "local-only"
        needs_tw = post_twitter and entry.get("twitter_url") == "local-only"
        
        if not (needs_yt or needs_fb or needs_ig or needs_tk or needs_li or needs_tg or needs_tw):
            continue
            
        if today_uploads >= videos_per_day:
            logging.info("Daily safety cap reached during catch-up uploads. Disabling remaining uploads, new tasks will run in local-only mode.")
            post_youtube = False
            post_facebook = False
            post_instagram = False
            post_tiktok = False
            post_linkedin = False
            post_telegram = False
            post_twitter = False
            break
            
        script = entry.get("script", "")
        logging.info(f"Catch-up: Processing pending uploads for '{topic}' at path: {video_path}")
        
        # 1. YouTube Upload
        if needs_yt:
            try:
                logging.info(f"Catch-up: Uploading '{topic}' to YouTube as {privacy}...")
                from app.services import youtube_upload
                youtube_url = youtube_upload.upload_video(
                    video_path=video_path,
                    subject=topic,
                    script=script,
                    privacy_status=privacy
                )
                if youtube_url:
                    logging.success(f"YouTube Upload URL: {youtube_url}")
                    entry["youtube_url"] = youtube_url
            except Exception as e:
                logging.error(f"YouTube catch-up upload failed for '{topic}': {e}")
                
        # 2. Facebook Page Upload
        if needs_fb:
            try:
                logging.info(f"Catch-up: Uploading '{topic}' to Facebook...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="facebook")
                fb_title = meta.get("title", f"AI Video: {topic}")
                fb_desc = meta.get("caption", f"Generated video about {topic}.\n\nScript:\n{script}")
                
                from app.services import meta_upload
                fb_res = meta_upload.upload_to_facebook(video_path, fb_title, fb_desc)
                if fb_res:
                    entry["facebook_url"] = fb_res.get("url")
            except Exception as e:
                logging.error(f"Facebook Page catch-up upload failed for '{topic}': {e}")
                
        # 3. Instagram Reels Upload
        if needs_ig:
            try:
                logging.info(f"Catch-up: Uploading '{topic}' to Instagram...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="instagram")
                ig_caption = f"{meta.get('title', '')}\n\n{meta.get('caption', '')}\n\n" + " ".join(meta.get("hashtags", []))
                
                from app.services import meta_upload
                ig_res = meta_upload.upload_to_instagram(video_path, ig_caption)
                if ig_res:
                    entry["instagram_url"] = ig_res.get("url")
            except Exception as e:
                logging.error(f"Instagram Reels catch-up upload failed for '{topic}': {e}")
                
        # 4. TikTok Upload
        if needs_tk:
            try:
                logging.info(f"Catch-up: Uploading '{topic}' to TikTok...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="tiktok")
                tk_caption = f"{meta.get('title', '')} " + " ".join(meta.get("hashtags", []))
                
                from app.services import tiktok_upload
                tk_res = tiktok_upload.upload_to_tiktok(video_path, tk_caption)
                if tk_res:
                    entry["tiktok_url"] = tk_res.get("url")
            except Exception as e:
                logging.error(f"TikTok catch-up upload failed for '{topic}': {e}")
                
        # 5. LinkedIn Upload
        if needs_li:
            try:
                logging.info(f"Catch-up: Uploading '{topic}' to LinkedIn...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="linkedin")
                li_caption = f"{meta.get('title', '')}\n\n{meta.get('caption', '')}\n\n" + " ".join(meta.get("hashtags", []))
                
                from app.services import linkedin_upload
                li_res = linkedin_upload.upload_to_linkedin(video_path, li_caption)
                if li_res:
                    entry["linkedin_url"] = li_res.get("url")
            except Exception as e:
                logging.error(f"LinkedIn catch-up upload failed for '{topic}': {e}")
                
        # 6. Telegram Upload
        if needs_tg:
            try:
                logging.info(f"Catch-up: Uploading '{topic}' to Telegram...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="telegram")
                tg_caption = f"⚡️ *{meta.get('title', '')}*\n\n{meta.get('caption', '')}\n\n" + " ".join(meta.get("hashtags", []))
                
                from app.services import telegram_upload
                tg_res = telegram_upload.upload_to_telegram(video_path, tg_caption)
                if tg_res:
                    entry["telegram_url"] = tg_res.get("url")
            except Exception as e:
                logging.error(f"Telegram catch-up upload failed for '{topic}': {e}")

        # 7. Twitter/X Upload
        if needs_tw:
            try:
                logging.info(f"Catch-up: Uploading '{topic}' to Twitter/X...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="tiktok") # fallback is tiktok, fits under 280 chars
                tw_caption = f"{meta.get('title', '')} " + " ".join(meta.get("hashtags", []))
                
                from app.services import twitter_upload
                tw_res = twitter_upload.upload_to_twitter(video_path, tw_caption)
                if tw_res:
                    entry["twitter_url"] = tw_res.get("url")
            except Exception as e:
                logging.error(f"Twitter catch-up upload failed for '{topic}': {e}")

        done_log[topic] = entry
        save_json(DONE_PATH, done_log)
        
        today_uploads += 1
        catchup_count += 1
        logging.info(f"Uploaded total today (after catchup): {today_uploads}/{videos_per_day}")
            
    if catchup_count > 0:
        logging.info(f"Catch-up uploads complete. Uploaded {catchup_count} previously offline videos.")

    if today_uploads >= videos_per_day:
        logging.info("Daily safety cap reached. Disabling remaining uploads, new tasks will run in local-only mode.")
        post_youtube = False
        post_facebook = False
        post_instagram = False
        post_tiktok = False
        post_linkedin = False
        post_telegram = False
        post_twitter = False
        
    # ── Viral Optimization: fetch trending data once for this run (cached daily) ──
    viral_trending_data = None
    if config.get("enable_viral_optimization", True):
        try:
            from skills.viral_optimize import trending_research
            viral_trending_data = trending_research(niche)
            logging.info(f"[Viral] Trending research loaded. Top keywords: {viral_trending_data.get('keywords', [])[:5]}")
        except Exception as ve:
            logging.warning(f"[Viral] Trending research skipped: {ve}")

    # Process topics
    # Process topics in parallel
    import threading
    import concurrent.futures

    class ProcessLock:
        def __init__(self, filepath):
            self.filepath = filepath
            self.acquired = False

        def __enter__(self):
            start_time = time.time()
            while time.time() - start_time < 1200:
                try:
                    fd = os.open(self.filepath, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(fd)
                    self.acquired = True
                    return self
                except FileExistsError:
                    time.sleep(5)
            try:
                mtime = os.path.getmtime(self.filepath)
                if time.time() - mtime > 900:
                    try:
                        os.remove(self.filepath)
                    except Exception:
                        pass
                    fd = os.open(self.filepath, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(fd)
                    self.acquired = True
                    return self
            except Exception:
                pass
            raise TimeoutError("Failed to acquire cross-process upload lock within 20 minutes.")

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.acquired:
                try:
                    os.remove(self.filepath)
                except Exception:
                    pass
                self.acquired = False

    done_log_lock = threading.Lock()
    queue_lock = threading.Lock()
    upload_lock = ProcessLock(os.path.join(PROJECT_ROOT, "upload.lock"))
    state_lock = threading.Lock()

    class ThreadState:
        def __init__(self):
            self.uploaded_in_this_run = 0
            self.post_youtube = post_youtube
            self.post_facebook_video = post_facebook_video
            self.post_facebook_image = post_facebook_image
            self.post_facebook_text = post_facebook_text
            self.post_instagram_video = post_instagram_video
            self.post_instagram_image = post_instagram_image
            self.post_linkedin_video = post_linkedin_video
            self.post_linkedin_image = post_linkedin_image
            self.post_linkedin_text = post_linkedin_text
            self.post_tiktok = post_tiktok
            self.post_telegram = post_telegram
            self.post_twitter = post_twitter

    thread_state = ThreadState()

    def process_topic_thread():
        nonlocal today_uploads
        
        while True:
            # 1. Pop topic safely
            with queue_lock:
                if not topics_queue:
                    logging.info("Queue is empty. Replenishing topics...")
                    with done_log_lock:
                        new_topics = brainstorm_topics(niche, done_log)
                    if new_topics:
                        topics_queue.extend(new_topics)
                        save_json(TOPICS_PATH, {"queue": topics_queue})
                    else:
                        logging.error("No topics brainstormed and queue is empty. Exiting thread.")
                        break
                
                # Check safety cap / quota before starting next generation
                with state_lock:
                    total_uploaded = today_uploads + thread_state.uploaded_in_this_run
                    if total_uploaded >= videos_per_day:
                        logging.info("Daily safety cap reached. Switching subsequent generations to local-only mode.")
                        thread_state.post_youtube = False
                        thread_state.post_facebook_video = False
                        thread_state.post_facebook_image = False
                        thread_state.post_facebook_text = False
                        thread_state.post_instagram_video = False
                        thread_state.post_instagram_image = False
                        thread_state.post_linkedin_video = False
                        thread_state.post_linkedin_image = False
                        thread_state.post_linkedin_text = False
                        thread_state.post_tiktok = False
                        thread_state.post_telegram = False
                        thread_state.post_twitter = False

                topic = topics_queue.pop(0)
                save_json(TOPICS_PATH, {"queue": topics_queue}) # Save state immediately

            # Calendar Scheduling Check
            if config.get("enable_calendar_scheduling", False):
                try:
                    import random
                    calendar_path = os.path.join(PROJECT_ROOT, "config", "calendar.json")
                    if os.path.exists(calendar_path):
                        with open(calendar_path, "r") as f:
                            cal_data = json.load(f)
                        slots = cal_data.get("optimal_slots", {})
                        logging.info(f"[Scheduler] Optimal publication slots configuration: {slots}")
                        max_delay = int(cal_data.get("random_delay_minutes_max", 15))
                        delay_seconds = random.randint(0, max_delay * 60)
                        test_mode = config.get("test_mode", False)
                        wait_time = min(delay_seconds, 15) if test_mode else delay_seconds
                        logging.info(f"[Scheduler] Spreading publication: applying randomized delay of {wait_time}s...")
                        time.sleep(wait_time)
                except Exception as cal_err:
                    logging.warning(f"[Scheduler] Calendar window check skipped: {cal_err}")

            logging.info(f"----------------------------------------")
            logging.info(f"Processing Topic: '{topic}'")

            # Get local state copy for this thread's generation step
            with state_lock:
                local_post_youtube = thread_state.post_youtube
                local_post_facebook_video = thread_state.post_facebook_video
                local_post_facebook_image = thread_state.post_facebook_image
                local_post_facebook_text = thread_state.post_facebook_text
                local_post_instagram_video = thread_state.post_instagram_video
                local_post_instagram_image = thread_state.post_instagram_image
                local_post_linkedin_video = thread_state.post_linkedin_video
                local_post_linkedin_image = thread_state.post_linkedin_image
                local_post_linkedin_text = thread_state.post_linkedin_text
                local_post_tiktok = thread_state.post_tiktok
                local_post_telegram = thread_state.post_telegram
                local_post_twitter = thread_state.post_twitter
                local_uploaded_in_this_run = thread_state.uploaded_in_this_run

            video_enabled = local_post_youtube or local_post_facebook_video or local_post_instagram_video or local_post_linkedin_video
            image_enabled = local_post_facebook_image or local_post_instagram_image or local_post_linkedin_image

            is_video = True
            if video_enabled and image_enabled:
                if (local_uploaded_in_this_run % 10) / 10.0 >= ratio_video_vs_image:
                    is_video = False
            elif not video_enabled and image_enabled:
                is_video = False

            if is_video:
                logging.info(f"Format chosen: Video")

                # ── Viral Optimization: get optimized titles/desc/hashtags/hook ──
                viral_pkg = None
                viral_hook_line = ""
                if config.get("enable_viral_optimization", True) and viral_trending_data:
                    try:
                        from skills.viral_optimize import get_viral_package
                        viral_pkg = get_viral_package(topic, niche,
                                                      platforms=["youtube_shorts","instagram","facebook","linkedin","tiktok"],
                                                      trending_data=viral_trending_data)
                        viral_hook_line = viral_pkg.get("hook", "")
                        logging.info(f"[Viral] Hook: {viral_hook_line}")
                    except Exception as ve:
                        logging.warning(f"[Viral] Package generation skipped for '{topic}': {ve}")

                # 1. Generate Script (inject viral hook as first line if available)
                script = generate_script(topic, niche)
                if not script:
                    logging.error(f"Failed to generate script for topic '{topic}'. Skipping.")
                    continue
                if viral_hook_line and script:
                    script = viral_hook_line + " " + script

                # 2. Run CLI Pipeline (stop at video, so it generates file locally)
                logging.info(f"Launching video pipeline for '{topic}'...")
                cmd = [
                    sys.executable,
                    "cli.py",
                    "--video-subject", topic,
                    "--video-script", script,
                    "--video-aspect", "9:16",
                    "--stop-at", "video"
                ]
                if config.get("use_ai_clips", False):
                    cmd.append("--use-ai-clips")
                if local_post_youtube:
                    cmd.append("--upload-youtube")
                    cmd.extend(["--youtube-privacy", privacy])

                try:
                    env = os.environ.copy()
                    env["PYTHONIOENCODING"] = "utf-8"
                    
                    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
                    
                    logging.info(f"Pipeline stdout:\n{proc.stdout}")
                    if proc.stderr:
                        logging.warning(f"Pipeline stderr:\n{proc.stderr}")
                        
                    if proc.returncode != 0:
                        logging.error(f"cli.py process returned non-zero code {proc.returncode}. Skipping topic.")
                        continue
                        
                    video_path = None
                    youtube_url = None
                    for line in proc.stdout.splitlines():
                        if line.strip().startswith('{"task_id":'):
                            try:
                                data = json.loads(line)
                                res_obj = data.get("result", {})
                                videos_list = res_obj.get("videos", [])
                                if videos_list:
                                    video_path = videos_list[0]
                                youtube_url = res_obj.get("youtube_url")
                                break
                            except Exception as e:
                                logging.warning(f"Failed to parse JSON output: {e}")

                    if video_path and os.path.exists(video_path):
                        logging.success(f"Video generated successfully at: {video_path}")
                        
                        urls_data = {
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "timestamp": datetime.now().isoformat(),
                            "format": "video",
                            "script": script,
                            "local_video_path": video_path,
                            "viral_hook": viral_hook_line if viral_hook_line else "",
                            "viral_keywords": viral_pkg.get("trending_keywords_used", []) if viral_pkg else [],
                            "credentials_status": {
                                "youtube": yt_status if post_youtube_orig else "skipped-disabled",
                                "facebook": meta_status if (post_facebook_video_orig or post_facebook_image_orig or post_facebook_text_orig) else "skipped-disabled",
                                "instagram": meta_status if (post_instagram_video_orig or post_instagram_image_orig) else "skipped-disabled",
                                "tiktok": tiktok_status if post_tiktok_orig else "skipped-disabled",
                                "linkedin": linkedin_status if (post_linkedin_video_orig or post_linkedin_image_orig or post_linkedin_text_orig) else "skipped-disabled",
                                "telegram": telegram_status if post_telegram_orig else "skipped-disabled",
                                "twitter": twitter_status if post_twitter_orig else "skipped-disabled"
                            }
                        }

                        # Now acquire upload_lock to post sequentially to social platforms!
                        with upload_lock:
                            # 1. YouTube status
                            if local_post_youtube:
                                if youtube_url:
                                    logging.success(f"YouTube Upload URL: {youtube_url}")
                                    urls_data["youtube_url"] = youtube_url
                                else:
                                    logging.error("YouTube upload requested but no youtube_url was returned by cli.py")
                                    urls_data["youtube_url"] = "local-only"
                            else:
                                urls_data["youtube_url"] = "local-only"

                            # 2. Facebook Page Upload
                            if local_post_facebook_video:
                                urls_data["facebook_url"] = "local-only"
                                try:
                                    logging.info("Generating Facebook Page social metadata...")
                                    if viral_pkg and "facebook" in viral_pkg.get("platforms", {}):
                                        fb_title = viral_pkg["platforms"]["facebook"]["title"]
                                        fb_desc  = viral_pkg["platforms"]["facebook"]["description"]
                                    else:
                                        from app.services.llm import generate_social_metadata
                                        meta     = generate_social_metadata(topic, script, platform="facebook")
                                        fb_title = meta.get("title", f"AI Video: {topic}")
                                        from app.services.cross_post import adapt_caption
                                        fb_desc  = adapt_caption("facebook", meta.get("caption", ""), meta.get("hashtags", []))
                                    
                                    from app.services import meta_upload
                                    fb_res = meta_upload.upload_to_facebook(video_path, fb_title, fb_desc)
                                    if fb_res:
                                        urls_data["facebook_url"] = fb_res.get("url")
                                except Exception as e:
                                    logging.error(f"Facebook Page upload failed for topic '{topic}': {e}")
                            else:
                                urls_data["facebook_url"] = "skipped"

                            # 3. Instagram Reels Upload
                            if local_post_instagram_video:
                                urls_data["instagram_url"] = "local-only"
                                try:
                                    logging.info("Generating Instagram Reels social metadata...")
                                    if viral_pkg and "instagram" in viral_pkg.get("platforms", {}):
                                        ig_plat  = viral_pkg["platforms"]["instagram"]
                                        ig_tags  = " ".join(ig_plat.get("hashtags", []))
                                        ig_caption = ig_plat["description"] + "\n\n" + ig_tags
                                    else:
                                        from app.services.llm import generate_social_metadata
                                        meta       = generate_social_metadata(topic, script, platform="instagram")
                                        from app.services.cross_post import adapt_caption
                                        ig_caption = adapt_caption("instagram", meta.get("caption", ""), meta.get("hashtags", []))
                                    
                                    from app.services import meta_upload
                                    ig_res = meta_upload.upload_to_instagram(video_path, ig_caption)
                                    if ig_res:
                                        urls_data["instagram_url"] = ig_res.get("url")
                                except Exception as e:
                                    logging.error(f"Instagram Reels upload failed for topic '{topic}': {e}")
                            else:
                                urls_data["instagram_url"] = "skipped"

                            # 4. TikTok Upload
                            if local_post_tiktok:
                                urls_data["tiktok_url"] = "local-only"
                                try:
                                    logging.info("Generating TikTok social metadata...")
                                    if viral_pkg and "tiktok" in viral_pkg.get("platforms", {}):
                                        tk_plat = viral_pkg["platforms"]["tiktok"]
                                        tk_caption = tk_plat["title"] + " " + " ".join(tk_plat.get("hashtags", []))
                                    else:
                                        from app.services.llm import generate_social_metadata
                                        meta = generate_social_metadata(topic, script, platform="tiktok")
                                        tk_caption = f"{meta.get('title', '')} " + " ".join(meta.get("hashtags", []))
                                    
                                    from app.services import tiktok_upload
                                    tk_res = tiktok_upload.upload_to_tiktok(video_path, tk_caption)
                                    if tk_res:
                                        urls_data["tiktok_url"] = tk_res.get("url")
                                except Exception as e:
                                    logging.error(f"TikTok upload failed for topic '{topic}': {e}")
                            else:
                                urls_data["tiktok_url"] = "skipped"

                            # 5. LinkedIn Upload
                            if local_post_linkedin_video:
                                urls_data["linkedin_url"] = "local-only"
                                try:
                                    logging.info("Generating LinkedIn social metadata...")
                                    if viral_pkg and "linkedin" in viral_pkg.get("platforms", {}):
                                        li_plat    = viral_pkg["platforms"]["linkedin"]
                                        li_tags    = " ".join(li_plat.get("hashtags", []))
                                        li_caption = li_plat["description"] + "\n\n" + li_tags
                                    else:
                                        from app.services.llm import generate_social_metadata
                                        meta       = generate_social_metadata(topic, script, platform="linkedin")
                                        from app.services.cross_post import adapt_caption
                                        li_caption = adapt_caption("linkedin", meta.get("caption", ""), meta.get("hashtags", []))
                                    
                                    from app.services import linkedin_upload
                                    li_res = linkedin_upload.upload_to_linkedin(video_path=video_path, text=li_caption)
                                    if li_res:
                                        urls_data["linkedin_url"] = li_res.get("url")
                                except Exception as e:
                                    logging.error(f"LinkedIn upload failed for topic '{topic}': {e}")
                            else:
                                urls_data["linkedin_url"] = "skipped"

                            # 6. Telegram Upload
                            if local_post_telegram:
                                urls_data["telegram_url"] = "local-only"
                                try:
                                    logging.info("Generating Telegram social metadata...")
                                    from app.services.llm import generate_social_metadata
                                    meta = generate_social_metadata(topic, script, platform="telegram")
                                    tg_caption = f"⚡️ *{meta.get('title', '')}*\n\n{meta.get('caption', '')}\n\n" + " ".join(meta.get("hashtags", []))
                                    
                                    from app.services import telegram_upload
                                    tg_res = telegram_upload.upload_to_telegram(video_path, tg_caption)
                                    if tg_res:
                                        urls_data["telegram_url"] = tg_res.get("url")
                                except Exception as e:
                                    logging.error(f"Telegram upload failed for topic '{topic}': {e}")
                            else:
                                urls_data["telegram_url"] = "skipped"

                            # 7. Twitter/X Upload
                            if local_post_twitter:
                                urls_data["twitter_url"] = "local-only"
                                try:
                                    logging.info("Generating Twitter/X social metadata...")
                                    from app.services.llm import generate_social_metadata
                                    meta = generate_social_metadata(topic, script, platform="tiktok")
                                    tw_caption = f"{meta.get('title', '')} " + " ".join(meta.get("hashtags", []))
                                    
                                    from app.services import twitter_upload
                                    tw_res = twitter_upload.upload_to_twitter(video_path, tw_caption)
                                    if tw_res:
                                        urls_data["twitter_url"] = tw_res.get("url")
                                except Exception as e:
                                    logging.error(f"Twitter upload failed for topic '{topic}': {e}")
                            else:
                                urls_data["twitter_url"] = "skipped"

                            # Save to done.json
                            with done_log_lock:
                                done_log[topic] = urls_data
                                save_json(DONE_PATH, done_log)
                                with state_lock:
                                    thread_state.uploaded_in_this_run += 1
                                    curr_total = today_uploads + thread_state.uploaded_in_this_run
                                logging.info(f"Uploaded total today (including failures logged as local-only): {curr_total}/{videos_per_day}")

                            trigger_post_engagement(config, topic, urls_data)

                    else:
                        logging.error(f"Could not find generated video path in pipeline output for '{topic}'. check logs.")

                except Exception as e:
                    logging.error(f"Exception raised during pipeline execution for '{topic}': {e}")
                    continue

            else:
                logging.info(f"Format chosen: Image + Text")
                try:
                    # 1. Generate visual post content via make_post skill
                    from skills.make_post import make_post
                    post_data = make_post(topic, niche)
                    image_path = post_data.get("image_path")
                    captions = post_data.get("captions", {})
                    
                    if image_path and os.path.exists(image_path):
                        logging.success(f"Image generated successfully at: {image_path}")
                        
                        urls_data = {
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "timestamp": datetime.now().isoformat(),
                            "format": "image_text",
                            "local_image_path": image_path,
                            "captions": captions,
                            "credentials_status": {
                                "facebook": meta_status if (post_facebook_image_orig or post_facebook_text_orig) else "skipped-disabled",
                                "instagram": meta_status if post_instagram_image_orig else "skipped-disabled",
                                "linkedin": linkedin_status if (post_linkedin_image_orig or post_linkedin_text_orig) else "skipped-disabled"
                            }
                        }

                        # Acquire upload lock for sequential Playwright posting!
                        with upload_lock:
                            # 1. Facebook Image Post
                            if local_post_facebook_image:
                                urls_data["facebook_url"] = "local-only"
                                try:
                                    from app.services.cross_post import adapt_image, adapt_caption
                                    fb_image = adapt_image(image_path, "facebook")
                                    fb_caption = adapt_caption("facebook", captions.get("facebook", captions.get("linkedin", topic)))
                                    fb_res = meta_upload.upload_image_to_facebook(fb_image, fb_caption)
                                    if fb_res:
                                        urls_data["facebook_url"] = fb_res.get("url")
                                except Exception as e:
                                    logging.error(f"Facebook Image post failed for topic '{topic}': {e}")
                            else:
                                urls_data["facebook_url"] = "skipped"

                            # 2. Instagram Image Post
                            if local_post_instagram_image:
                                urls_data["instagram_url"] = "local-only"
                                try:
                                    from app.services.cross_post import adapt_image, adapt_caption
                                    ig_image = adapt_image(image_path, "instagram")
                                    ig_caption = adapt_caption("instagram", captions.get("instagram", captions.get("linkedin", topic)))
                                    ig_res = meta_upload.upload_image_to_instagram(ig_image, ig_caption)
                                    if ig_res:
                                        urls_data["instagram_url"] = ig_res.get("url")
                                except Exception as e:
                                    logging.error(f"Instagram Image post failed for topic '{topic}': {e}")
                            else:
                                urls_data["instagram_url"] = "skipped"

                            # 3. LinkedIn Image Post
                            if local_post_linkedin_image:
                                urls_data["linkedin_url"] = "local-only"
                                try:
                                    from app.services.cross_post import adapt_image, adapt_caption
                                    li_image = adapt_image(image_path, "linkedin")
                                    li_caption = adapt_caption("linkedin", captions.get("linkedin", topic))
                                    li_res = linkedin_upload.upload_to_linkedin(image_path=li_image, text=li_caption)
                                    if li_res:
                                        urls_data["linkedin_url"] = li_res.get("url")
                                except Exception as e:
                                    logging.error(f"LinkedIn Image post failed for topic '{topic}': {e}")
                            else:
                                urls_data["linkedin_url"] = "skipped"

                            # Save to done_log
                            with done_log_lock:
                                done_log[topic] = urls_data
                                save_json(DONE_PATH, done_log)
                                with state_lock:
                                    thread_state.uploaded_in_this_run += 1
                                    curr_total = today_uploads + thread_state.uploaded_in_this_run
                                logging.info(f"Uploaded total today (including failures logged as local-only): {curr_total}/{videos_per_day}")

                            trigger_post_engagement(config, topic, urls_data)

                    else:
                        logging.error(f"Image post generation failed for topic '{topic}'")
                except Exception as e:
                    logging.error(f"Exception raised during image post execution for '{topic}': {e}")
                    continue

    # Start thread pool for concurrent video generations
    max_workers = 2
    logging.info(f"Starting concurrent generation pool with {max_workers} worker threads...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_topic_thread) for _ in range(max_workers)]
        concurrent.futures.wait(futures)
            
    # Trigger automatic AI image post flow for FB/IG
    try:
        logging.info("Triggering automatic AI image post flow for FB/IG...")
        from app.services.image_factory import run_image_post_flow
        img_res = run_image_post_flow()
        logging.info(f"Image post flow execution finished: {img_res}")
    except Exception as img_err:
        logging.error(f"Image post flow failed to run: {img_err}")

    # Trigger Analytics Pull & Performance Dashboard
    if config.get("enable_analytics_pull", False):
        try:
            logging.info("Triggering performance metrics pull and dashboard generation...")
            from app.services.analytics import run_analytics_pull, generate_analytics_summary_markdown
            report = run_analytics_pull()
            dashboard = generate_analytics_summary_markdown(report)
            logging.info(dashboard)
        except Exception as stats_err:
            logging.error(f"Performance analytics pull failed: {stats_err}")

    logging.info("Factory run finished.")
    logging.info("========================================")

if __name__ == "__main__":
    # Custom logger success level helper
    logging.SUCCESS = 25
    logging.addLevelName(logging.SUCCESS, "SUCCESS")
    def success(message, *args, **kws):
        logging.log(logging.SUCCESS, message, *args, **kws)
    logging.success = success
    
    main()
