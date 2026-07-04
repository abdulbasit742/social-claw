import requests
import json
import os

PROXY_URL = "http://172.30.10.10:3128"
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

creds_file = "meta_credentials.json"
if os.path.exists(creds_file):
    with open(creds_file, "r") as f:
        creds = json.load(f)

page_id = creds.get("page_id")
access_token = creds.get("access_token")

url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
print(f"URL: {url}")

# Create a small dummy text file and rename to jpg just to see if the upload request structure is verified or what is wrong
with open("dummy.jpg", "wb") as f:
    f.write(b"dummy image data")

payload = {
    "access_token": access_token,
    "caption": "Test post from Antigravity"
}

files = {
    "source": ("dummy.jpg", open("dummy.jpg", "rb"), "image/jpeg")
}

try:
    res = requests.post(url, data=payload, files=files, proxies=PROXIES)
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)

# Clean up
if os.path.exists("dummy.jpg"):
    os.remove("dummy.jpg")
