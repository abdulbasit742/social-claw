import os
import time
import httplib2
import urllib.parse
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import google.oauth2.credentials
from loguru import logger
from app.services.llm import generate_social_metadata

# YouTube API settings
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

def get_authenticated_service():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    client_secrets_file = os.path.join(repo_root, "client_secret.json")
    token_file = os.path.join(repo_root, "youtube_token.json")

    if not os.path.exists(client_secrets_file):
        raise FileNotFoundError(
            f"client_secret.json not found at {client_secrets_file}. "
            "Please create Google Cloud Credentials and place the file in the repository root."
        )

    credentials = None
    if os.path.exists(token_file):
        try:
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            logger.warning(f"Error loading youtube_token.json: {e}")

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("Refreshing expired YouTube OAuth credentials...")
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
        else:
            logger.info("Initializing new YouTube OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            credentials = flow.run_local_server(port=0, open_browser=False)
            
        with open(token_file, 'w') as token:
            token.write(credentials.to_json())
            logger.info(f"Saved YouTube OAuth credentials to {token_file}")

    # Build the authorized HTTP client with proxy support
    import google_auth_httplib2
    proxy_info = httplib2.proxy_info_from_environment()
    if proxy_info:
        logger.info(f"Using environment proxy for YouTube API: {proxy_info.proxy_host}:{proxy_info.proxy_port}")
    http = httplib2.Http(proxy_info=proxy_info)
    http.follow_redirects = False
    authorized_http = google_auth_httplib2.AuthorizedHttp(credentials, http=http)
    
    return build(API_SERVICE_NAME, API_VERSION, http=authorized_http)

def upload_video(video_path: str, subject: str, script: str = "", privacy_status: str = "unlisted"):
    if not os.path.exists(video_path):
        logger.error(f"Video file to upload does not exist: {video_path}")
        return None

    logger.info("Generating metadata via Ollama...")
    try:
        meta = generate_social_metadata(subject, script, platform="youtube_shorts")
        title = meta.get("title", f"AI Video: {subject}")
        description = meta.get("caption", f"Generated video about {subject}.")
        hashtags = meta.get("hashtags", [])
        
        # Clean tags (strip '#' and make lowercase/clean)
        tags = [tag.lstrip("#").strip() for tag in hashtags if tag.strip()]
        # Append standard tags
        tags.extend(["ai", "shorts", "automation"])
    except Exception as e:
        logger.warning(f"Metadata generation failed, using fallback values: {e}")
        title = f"AI Video: {subject[:50]}"
        description = f"Generated video about {subject}.\n\nScript:\n{script}"
        tags = ["ai", "shorts"]

    # Limit title length to 100 characters for YouTube
    if len(title) > 100:
        title = title[:97] + "..."

    logger.info(f"YouTube Upload Details:")
    logger.info(f"  Title: {title}")
    logger.info(f"  Description: {description}")
    logger.info(f"  Tags: {tags}")
    logger.info(f"  Privacy: {privacy_status}")

    try:
        youtube = get_authenticated_service()
    except Exception as auth_err:
        logger.error(f"Failed to authenticate YouTube API: {auth_err}")
        return None

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22' # People & Blogs
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype='video/mp4',
        chunksize=1024*1024,
        resumable=True
    )

    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    logger.info(f"Uploading {video_path} to YouTube...")
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Uploaded {int(status.progress() * 100)}%...")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                logger.warning(f"Temporary server error: {e.resp.status}. Retrying...")
                time.sleep(2)
            else:
                logger.error(f"HTTP Error during upload: {e}")
                raise
        except Exception as e:
            logger.error(f"Error during upload chunk: {e}")
            raise

    video_id = response.get('id')
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.success(f"Successfully uploaded video to YouTube! URL: {video_url}")
    logger.info("Quota Note: This upload consumed 1,600 units of your 10,000 daily quota (~6 uploads per day).")
    
    return video_url

if __name__ == "__main__":
    # Allow running directly as a script to verify upload or do simple upload tests
    import sys
    if len(sys.argv) < 3:
        print("Usage: python youtube_upload.py <video_path> <subject> [script]")
        sys.exit(1)
    
    vid_path = sys.argv[1]
    subj = sys.argv[2]
    sc = sys.argv[3] if len(sys.argv) > 3 else ""
    upload_video(vid_path, subj, sc)
