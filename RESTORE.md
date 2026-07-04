# Restore Guide - Autonomous Video Factory Setup

This guide documents the steps required to restore and run this autonomous video factory setup on a new Windows PC.

---

## 1. System Pre-requisites
Ensure the following software is installed on the target machine:
* **Python 3.10 or 3.11** (Ensure it is added to the system PATH).
* **Git** for cloning the repository.
* **FFmpeg**: Download and extract FFmpeg, and add its `bin/` directory to the system environment variables PATH.
* **Ollama**: Install [Ollama for Windows](https://ollama.com/) and pull the required model:
  ```powershell
  ollama pull qwen2.5:7b
  ```
* **Tailscale**: Install Tailscale and ensure a Funnel is configured if you need to expose public URLs for TikTok/Instagram webhooks or video pull requests.

---

## 2. Code Restoration Steps
Run these commands in a PowerShell window:

1. **Clone the private repository**:
   ```powershell
   git clone https://github.com/abdulbasit742/video-factory.git
   cd video-factory
   ```
2. **Create and activate the virtual environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. **Configure Eduroam Proxy environment variables** (if running behind a restricted network proxy):
   ```powershell
   $env:HTTP_PROXY="http://172.30.10.10:3128"
   $env:HTTPS_PROXY="http://172.30.10.10:3128"
   $env:http_proxy="http://172.30.10.10:3128"
   $env:https_proxy="http://172.30.10.10:3128"
   $env:NO_PROXY="localhost,127.0.0.1"
   $env:no_proxy="localhost,127.0.0.1"
   ```
4. **Install Python dependencies**:
   ```powershell
   pip install -r requirements
   ```

---

## 3. Restoring Ignored Credentials (Manual Steps)
Because credentials contain secrets, they are excluded from the repository via `.gitignore`. You must manually create or copy these files into the project root directory (`C:\Users\absh5\MoneyPrinterTurbo` or your new cloned directory):

### YouTube Publishing
* **`client_secret.json`**: Desktop OAuth client secrets downloaded from the Google Cloud Console.
* **`youtube_token.json`**: Generated automatically after running authentication once.

### Facebook & Instagram Reels
* **`meta_credentials.json`**:
  ```json
  {
    "app_id": "<app_id>",
    "app_secret": "<app_secret>",
    "page_id": "<page_id>",
    "instagram_business_account_id": "<instagram_business_account_id>",
    "access_token": "<access_token>"
  }
  ```

### TikTok Posting
* **`tiktok_credentials.json`**:
  ```json
  {
    "client_key": "<client_key>",
    "client_secret": "<client_secret>",
    "access_token": "<access_token>",
    "refresh_token": "<refresh_token>"
  }
  ```

### LinkedIn Feed Share
* **`linkedin_credentials.json`**:
  ```json
  {
    "client_id": "<client_id>",
    "client_secret": "<client_secret>",
    "access_token": "<access_token>",
    "refresh_token": "<refresh_token>",
    "person_urn": "urn:li:person:<id>"
  }
  ```

### Telegram Channel Bot
* **`telegram_credentials.json`**:
  ```json
  {
    "bot_token": "<bot_token>",
    "chat_id": "<chat_id_or_channel_username>"
  }
  ```

---

## 4. Verification & Running
Verify that the setup is completely configured and working by running the pre-flight checks:
```powershell
.\venv\Scripts\python.exe scripts\pre_flight_check.py
```
To run the automated loop manually or schedule it:
```powershell
.\venv\Scripts\python.exe scripts\auto_factory.py
```
