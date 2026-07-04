import os
import json
import requests
import sys
from datetime import datetime

# Set working directory to project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts import auto_factory
from app.services import meta_upload
from app.services import tiktok_upload
from app.services import linkedin_upload
from app.services import telegram_upload
from app.services import twitter_upload

# System Proxy
PROXIES = {"http": "http://172.30.10.10:3128", "https": "http://172.30.10.10:3128"}

def check_internet():
    try:
        r = requests.get("https://www.google.com", proxies=PROXIES, timeout=5)
        return "PASS" if r.status_code == 200 else "FAIL"
    except Exception:
        return "FAIL"

def check_ollama():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            if any("qwen2.5:7b" in m for m in models):
                return "PASS"
            return "MISSING MODEL"
        return "FAIL"
    except Exception:
        return "FAIL"

def check_yt():
    status = auto_factory.check_youtube_credentials()
    if status in ["ok", "refreshed"]:
        return "PASS"
    elif status == "skipped-missing":
        return "MISSING"
    return "EXPIRED"

def check_meta():
    status = meta_upload.check_meta_credentials()
    if status in ["ok", "refreshed"]:
        return "PASS"
    elif status == "skipped-missing":
        return "MISSING"
    return "EXPIRED"

def check_tiktok():
    status = tiktok_upload.check_tiktok_credentials()
    if status in ["ok", "refreshed"]:
        return "PASS"
    elif status == "skipped-missing":
        return "MISSING"
    return "EXPIRED"

def check_linkedin():
    status = linkedin_upload.check_linkedin_credentials()
    if status in ["ok", "refreshed"]:
        return "PASS"
    elif status == "skipped-missing":
        return "MISSING"
    return "EXPIRED"

def check_telegram():
    status = telegram_upload.check_telegram_credentials()
    if status in ["ok"]:
        return "PASS"
    elif status == "skipped-missing":
        return "MISSING"
    return "EXPIRED"

def check_twitter():
    status = twitter_upload.check_twitter_credentials()
    if status in ["ok"]:
        return "PASS"
    elif status == "skipped-missing":
        return "MISSING"
    return "EXPIRED"

def check_quota():
    try:
        config = auto_factory.load_config()
        cap = int(config.get("videos_per_day", 5))
        done = auto_factory.load_json(auto_factory.DONE_PATH)
        today_uploads = auto_factory.count_today_uploads(done)
        remaining = cap - today_uploads
        return f"{today_uploads}/{cap} Uploaded ({remaining} Left)"
    except Exception:
        return "ERROR"

def main():
    internet = check_internet()
    ollama = check_ollama()
    yt = check_yt()
    meta = check_meta()
    tiktok = check_tiktok()
    linkedin = check_linkedin()
    telegram = check_telegram()
    twitter = check_twitter()
    quota = check_quota()

    print("\n=== PRE-FLIGHT HEALTH CHECK ===")
    print(f"{'Component':<25} | {'Status':<30}")
    print("-" * 60)
    print(f"{'Eduroam Proxy/Internet':<25} | {internet:<30}")
    print(f"{'Ollama (qwen2.5:7b)':<25} | {ollama:<30}")
    print(f"{'YouTube Credentials':<25} | {yt:<30}")
    print(f"{'Meta Credentials':<25} | {meta:<30}")
    print(f"{'TikTok Credentials':<25} | {tiktok:<30}")
    print(f"{'LinkedIn Credentials':<25} | {linkedin:<30}")
    print(f"{'Telegram Credentials':<25} | {telegram:<30}")
    print(f"{'Twitter Credentials':<25} | {twitter:<30}")
    print(f"{'Daily Quota Progress':<25} | {quota:<30}")
    print("=" * 60)

if __name__ == "__main__":
    main()
