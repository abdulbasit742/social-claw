#!/usr/bin/env python3
"""
LinkedIn OAuth Setup Tool
=========================
Yeh script ek local server start karta hai jis par LinkedIn redirect karega.
Browser automatically open hoga. Aapko sirf LinkedIn par login kar ke "Allow" click karna hai.
Token auto-save ho jayega linkedin_credentials.json mein.

USAGE:
  python scripts/linkedin_oauth.py --client_id YOUR_ID --client_secret YOUR_SECRET

"""

import os
import sys
import json
import time
import threading
import webbrowser
import argparse
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

# ─────────────────────────── Config ────────────────────────────
PORT        = 8765
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPE       = "openid profile email w_member_social"   # LinkedIn v2 scopes
STATE       = "linkedin_oauth_state_xyz"
CREDS_FILE  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "linkedin_credentials.json")

# ─────────────────────────── Globals ───────────────────────────
auth_code   = None
server_done = threading.Event()
client_id_g = ""
client_secret_g = ""

# ─────────────────────────── HTTP Handler ──────────────────────
class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default server logs

    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)

        if parsed.path == "/callback":
            params = parse_qs(parsed.query)

            error = params.get("error", [None])[0]
            if error:
                error_desc = params.get("error_description", ["Unknown error"])[0]
                self._send_html(f"""
                <html><body style='font-family:sans-serif;padding:40px;background:#1a1a2e;color:#e94560'>
                <h1>❌ Authorization Failed</h1>
                <p>Error: <b>{error}</b></p>
                <p>{error_desc}</p>
                <p>Aap yeh window band kar sakte hain.</p>
                </body></html>
                """)
                server_done.set()
                return

            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]

            if state != STATE:
                self._send_html("<html><body><h1>Invalid state!</h1></body></html>")
                server_done.set()
                return

            if code:
                auth_code = code
                self._send_html("""
                <html><body style='font-family:sans-serif;padding:40px;background:#0f3460;color:#e2e8f0;text-align:center'>
                <h1 style='color:#16c79a;font-size:48px'>✅ Authorization Successful!</h1>
                <h2>LinkedIn Token Exchange Ho Raha Hai...</h2>
                <p style='font-size:18px'>Kuch seconds mein aapka LinkedIn account connect ho jayega.</p>
                <p>Aap yeh window band kar sakte hain.</p>
                <div style='margin-top:30px;padding:20px;background:#1a1a2e;border-radius:12px'>
                <p style='color:#ffd460'>📋 Token terminal mein save ho raha hai...</p>
                </div>
                </body></html>
                """)
                server_done.set()
            else:
                self._send_html("<html><body><h1>No code received!</h1></body></html>")
                server_done.set()

        elif parsed.path == "/":
            self._send_html("""
            <html><body style='font-family:sans-serif;padding:40px;background:#0f3460;color:#e2e8f0;text-align:center'>
            <h1>LinkedIn OAuth Server Running</h1>
            <p>LinkedIn callback ka intezaar hai...</p>
            </body></html>
            """)
        else:
            self.send_response(404)
            self.end_headers()

    def _send_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.strip().encode("utf-8"))


# ─────────────────────────── Token Exchange ────────────────────
def exchange_code_for_token(code: str, client_id: str, client_secret: str) -> dict:
    print("\n🔄 Authorization code mila! Token exchange ho raha hai...")
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     client_id,
        "client_secret": client_secret,
    }
    proxies = {}
    try:
        from app.config import config
        proxies = config.proxy or {}
    except Exception:
        pass

    resp = requests.post(url, data=data, proxies=proxies, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────── Fetch Person URN ──────────────────
def fetch_person_urn(access_token: str) -> str:
    print("👤 LinkedIn profile fetch ho raha hai...")
    proxies = {}
    try:
        from app.config import config
        proxies = config.proxy or {}
    except Exception:
        pass

    headers = {"Authorization": f"Bearer {access_token}"}

    # Try OpenID userinfo first (works with openid scope)
    try:
        r = requests.get("https://api.linkedin.com/v2/userinfo",
                         headers=headers, proxies=proxies, timeout=15)
        if r.status_code == 200:
            data = r.json()
            sub  = data.get("sub", "")
            name = data.get("name", "")
            print(f"   ✅ Profile: {name}  |  sub={sub}")
            return f"urn:li:person:{sub}"
    except Exception:
        pass

    # Fallback to /v2/me
    r = requests.get("https://api.linkedin.com/v2/me",
                     headers=headers, proxies=proxies, timeout=15)
    r.raise_for_status()
    data = r.json()
    uid  = data.get("id", "")
    fname = data.get("localizedFirstName", "")
    lname = data.get("localizedLastName", "")
    print(f"   ✅ Profile: {fname} {lname}  |  id={uid}")
    return f"urn:li:person:{uid}"


# ─────────────────────────── Save Credentials ──────────────────
def save_credentials(client_id, client_secret, token_data, person_urn):
    creds = {
        "client_id":     client_id,
        "client_secret": client_secret,
        "access_token":  token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_in":    token_data.get("expires_in", 0),
        "person_urn":    person_urn,
        "scope":         token_data.get("scope", ""),
    }
    with open(CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)
    print(f"\n💾 Credentials saved to: {CREDS_FILE}")
    return creds


# ─────────────────────────── Main ──────────────────────────────
def main():
    global client_id_g, client_secret_g

    parser = argparse.ArgumentParser(description="LinkedIn OAuth Setup Tool")
    parser.add_argument("--client_id",     required=True, help="LinkedIn App Client ID")
    parser.add_argument("--client_secret", required=True, help="LinkedIn App Client Secret")
    args = parser.parse_args()

    client_id_g     = args.client_id
    client_secret_g = args.client_secret

    # Build authorization URL
    auth_params = {
        "response_type": "code",
        "client_id":     client_id_g,
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPE,
        "state":         STATE,
    }
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(auth_params)

    # Start local HTTP server in background thread
    server = HTTPServer(("localhost", PORT), OAuthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print("\n" + "="*60)
    print("  🔗 LinkedIn OAuth Setup Tool")
    print("="*60)
    print(f"\n✅ Local callback server started on port {PORT}")
    print(f"\n🌐 Browser mein Authorization URL open ho rahi hai...")
    print(f"\n   Agar browser auto-open na ho to manually yeh URL open karein:\n")
    print(f"   {auth_url}\n")
    print("="*60)
    print("   ⏳ LinkedIn par 'Allow' click karein...")
    print("="*60 + "\n")

    # Open browser after short delay
    time.sleep(1.5)
    webbrowser.open(auth_url)

    # Wait for callback (timeout 5 min)
    got_it = server_done.wait(timeout=300)
    server.shutdown()

    if not got_it:
        print("❌ Timeout! 5 minute mein koi response nahi aaya.")
        sys.exit(1)

    if not auth_code:
        print("❌ Authorization code nahi mila. Error check karein upar.")
        sys.exit(1)

    # Exchange code → token
    try:
        token_data = exchange_code_for_token(auth_code, client_id_g, client_secret_g)
    except Exception as e:
        print(f"❌ Token exchange failed: {e}")
        sys.exit(1)

    access_token = token_data.get("access_token")
    if not access_token:
        print(f"❌ Access token nahi mila! Response: {token_data}")
        sys.exit(1)

    print(f"   ✅ Access Token mila! (expires_in={token_data.get('expires_in')}s)")

    # Fetch person URN
    try:
        person_urn = fetch_person_urn(access_token)
    except Exception as e:
        print(f"❌ Profile fetch failed: {e}")
        sys.exit(1)

    # Save everything
    creds = save_credentials(client_id_g, client_secret_g, token_data, person_urn)

    print("\n" + "="*60)
    print("  🎉 LinkedIn OAuth COMPLETE!")
    print("="*60)
    print(f"  👤 Person URN : {creds['person_urn']}")
    print(f"  🔑 Token      : {creds['access_token'][:30]}...")
    print(f"  📁 Saved to   : {CREDS_FILE}")
    print("="*60)
    print("\n✅ Ab auto_factory.py chal sakti hai! LinkedIn par videos post hongi.\n")


if __name__ == "__main__":
    main()
