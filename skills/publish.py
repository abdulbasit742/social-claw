import sys
import os
import argparse
import json

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts import auto_factory
from app.services import youtube_upload
from app.services import meta_upload
from app.services import tiktok_upload
from app.services import linkedin_upload
from app.services import telegram_upload
from app.services import twitter_upload

def publish_video(video_path: str, topic: str, script: str) -> dict:
    if not os.path.exists(video_path):
        raise Exception(f"Video file not found: {video_path}")
        
    config = auto_factory.load_config()
    privacy = config.get("privacy", "unlisted")
    post_youtube = config.get("post_youtube", True)
    post_facebook = config.get("post_facebook", True)
    post_instagram = config.get("post_instagram", True)
    post_tiktok = config.get("post_tiktok", False)
    post_linkedin = config.get("post_linkedin", False)
    post_telegram = config.get("post_telegram", False)
    post_twitter = config.get("post_twitter", False)
    
    results = {}
    
    # 1. YouTube Upload
    if post_youtube:
        yt_status = auto_factory.check_youtube_credentials()
        if yt_status in ["ok", "refreshed"]:
            try:
                print("Uploading to YouTube...")
                url = youtube_upload.upload_video(
                    video_path=video_path,
                    subject=topic,
                    script=script,
                    privacy_status=privacy
                )
                if url:
                    results["youtube_url"] = url
                    print(f"Uploaded successfully to YouTube: {url}")
            except Exception as e:
                print(f"YouTube upload failed: {e}", file=sys.stderr)
        else:
            print(f"Skipping YouTube upload due to credentials status: {yt_status}")
            
    # 2. Facebook Page Upload
    if post_facebook:
        meta_status = meta_upload.check_meta_credentials()
        if meta_status in ["ok", "refreshed"]:
            try:
                print("Uploading to Facebook...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="facebook")
                fb_title = meta.get("title", f"AI Video: {topic}")
                fb_desc = meta.get("caption", f"Generated video about {topic}.\n\nScript:\n{script}")
                
                fb_res = meta_upload.upload_to_facebook(video_path, fb_title, fb_desc)
                if fb_res:
                    url = fb_res.get("url")
                    results["facebook_url"] = url
                    print(f"Uploaded successfully to Facebook: {url}")
            except Exception as e:
                print(f"Facebook upload failed: {e}", file=sys.stderr)
        else:
            print(f"Skipping Facebook upload due to credentials status: {meta_status}")
            
    # 3. Instagram Reels Upload
    if post_instagram:
        meta_status = meta_upload.check_meta_credentials()
        if meta_status in ["ok", "refreshed"]:
            try:
                print("Uploading to Instagram...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="instagram")
                ig_caption = f"{meta.get('title', '')}\n\n{meta.get('caption', '')}\n\n" + " ".join(meta.get("hashtags", []))
                
                ig_res = meta_upload.upload_to_instagram(video_path, ig_caption)
                if ig_res:
                    url = ig_res.get("url")
                    results["instagram_url"] = url
                    print(f"Uploaded successfully to Instagram: {url}")
            except Exception as e:
                print(f"Instagram upload failed: {e}", file=sys.stderr)
        else:
            print(f"Skipping Instagram upload due to credentials status: {meta_status}")
            
    # 4. TikTok Upload
    if post_tiktok:
        tiktok_status = tiktok_upload.check_tiktok_credentials()
        if tiktok_status in ["ok", "refreshed"]:
            try:
                print("Uploading to TikTok...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="tiktok")
                tk_caption = f"{meta.get('title', '')} " + " ".join(meta.get("hashtags", []))
                
                tk_res = tiktok_upload.upload_to_tiktok(video_path, tk_caption)
                if tk_res:
                    url = tk_res.get("url")
                    results["tiktok_url"] = url
                    print(f"Uploaded successfully to TikTok: {url}")
            except Exception as e:
                print(f"TikTok upload failed: {e}", file=sys.stderr)
        else:
            print(f"Skipping TikTok upload due to credentials status: {tiktok_status}")
            
    # 5. LinkedIn Upload
    if post_linkedin:
        linkedin_status = linkedin_upload.check_linkedin_credentials()
        if linkedin_status in ["ok", "refreshed"]:
            try:
                print("Uploading to LinkedIn...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="linkedin")
                li_caption = f"{meta.get('title', '')}\n\n{meta.get('caption', '')}\n\n" + " ".join(meta.get("hashtags", []))
                
                li_res = linkedin_upload.upload_to_linkedin(video_path, li_caption)
                if li_res:
                    url = li_res.get("url")
                    results["linkedin_url"] = url
                    print(f"Uploaded successfully to LinkedIn: {url}")
            except Exception as e:
                print(f"LinkedIn upload failed: {e}", file=sys.stderr)
        else:
            print(f"Skipping LinkedIn upload due to credentials status: {linkedin_status}")
            
    # 6. Telegram Upload
    if post_telegram:
        telegram_status = telegram_upload.check_telegram_credentials()
        if telegram_status in ["ok"]:
            try:
                print("Uploading to Telegram...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="telegram")
                tg_caption = f"⚡️ *{meta.get('title', '')}*\n\n{meta.get('caption', '')}\n\n" + " ".join(meta.get("hashtags", []))
                
                tg_res = telegram_upload.upload_to_telegram(video_path, tg_caption)
                if tg_res:
                    url = tg_res.get("url")
                    results["telegram_url"] = url
                    print(f"Uploaded successfully to Telegram: {url}")
            except Exception as e:
                print(f"Telegram upload failed: {e}", file=sys.stderr)
        else:
            print(f"Skipping Telegram upload due to credentials status: {telegram_status}")
            
    # 7. Twitter/X Upload
    if post_twitter:
        twitter_status = twitter_upload.check_twitter_credentials()
        if twitter_status in ["ok"]:
            try:
                print("Uploading to Twitter/X...")
                from app.services.llm import generate_social_metadata
                meta = generate_social_metadata(topic, script, platform="tiktok") # fallback is tiktok, fits under 280 chars
                tw_caption = f"{meta.get('title', '')} " + " ".join(meta.get("hashtags", []))
                
                tw_res = twitter_upload.upload_to_twitter(video_path, tw_caption)
                if tw_res:
                    url = tw_res.get("url")
                    results["twitter_url"] = url
                    print(f"Uploaded successfully to Twitter/X: {url}")
            except Exception as e:
                print(f"Twitter upload failed: {e}", file=sys.stderr)
        else:
            print(f"Skipping Twitter upload due to credentials status: {twitter_status}")
            
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-path", required=True, help="Path to mp4 file")
    parser.add_argument("--topic", required=True, help="Video topic")
    parser.add_argument("--script", required=True, help="Video script")
    args = parser.parse_args()
    
    try:
        urls = publish_video(args.video_path, args.topic, args.script)
        print(f"RESULT_URLS:{json.dumps(urls)}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
