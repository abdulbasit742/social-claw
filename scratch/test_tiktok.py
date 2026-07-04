import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from app.services.tiktok_upload import check_tiktok_credentials, load_tiktok_credentials

print("Loading TikTok credentials...")
creds = load_tiktok_credentials()
print(f"Loaded client_key: {creds.get('client_key')}")

print("\nRunning check_tiktok_credentials()...")
status = check_tiktok_credentials()
print(f"TikTok credentials status: {status}")
