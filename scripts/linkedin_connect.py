#!/usr/bin/env python3
"""
LinkedIn One-Click Connect Tool
================================
No developer app needed. Sirf email + password.
Browser mein http://localhost:9090 open hoga.
"""

import os, sys, json, threading, webbrowser, time
from flask import Flask, request, jsonify, render_template_string

# ── Paths ──────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
CREDS_FILE = os.path.join(project_root, "linkedin_credentials.json")

# ── Flask App ──────────────────────────────────────────────────
app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>LinkedIn Connect</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
  *{margin:0;padding:0;box-sizing:border-box}
  body{
    font-family:'Inter',sans-serif;
    min-height:100vh;
    background:linear-gradient(135deg,#0a0a0f 0%,#0d1117 40%,#001832 100%);
    display:flex;align-items:center;justify-content:center;
  }
  .card{
    background:rgba(255,255,255,0.04);
    border:1px solid rgba(255,255,255,0.1);
    backdrop-filter:blur(24px);
    border-radius:24px;
    padding:48px 40px;
    width:420px;
    box-shadow:0 32px 80px rgba(0,0,0,0.5);
    animation:fadeUp .5s ease;
  }
  @keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
  .logo{
    display:flex;align-items:center;gap:12px;margin-bottom:32px;
  }
  .logo-icon{
    width:48px;height:48px;border-radius:12px;
    background:linear-gradient(135deg,#0077b5,#00a0dc);
    display:flex;align-items:center;justify-content:center;
    font-size:24px;font-weight:800;color:#fff;
    box-shadow:0 8px 24px rgba(0,119,181,0.4);
  }
  .logo-text{font-size:22px;font-weight:700;color:#fff}
  .logo-sub{font-size:12px;color:#64748b;margin-top:2px}
  h2{color:#fff;font-size:26px;font-weight:700;margin-bottom:6px}
  .subtitle{color:#64748b;font-size:14px;margin-bottom:32px}
  label{display:block;font-size:13px;font-weight:600;color:#94a3b8;margin-bottom:6px}
  input{
    width:100%;padding:14px 16px;
    background:rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.12);
    border-radius:12px;color:#fff;font-size:15px;
    font-family:'Inter',sans-serif;
    transition:all .2s;outline:none;margin-bottom:20px;
  }
  input::placeholder{color:#475569}
  input:focus{border-color:#0077b5;background:rgba(0,119,181,0.08);box-shadow:0 0 0 3px rgba(0,119,181,0.15)}
  .btn{
    width:100%;padding:16px;
    background:linear-gradient(135deg,#0077b5 0%,#00a0dc 100%);
    border:none;border-radius:12px;color:#fff;
    font-size:16px;font-weight:700;cursor:pointer;
    font-family:'Inter',sans-serif;
    transition:all .2s;letter-spacing:.3px;
    box-shadow:0 8px 24px rgba(0,119,181,0.35);
  }
  .btn:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 12px 32px rgba(0,119,181,0.5)}
  .btn:active:not(:disabled){transform:translateY(0)}
  .btn:disabled{opacity:.6;cursor:not-allowed;transform:none}
  .status{
    margin-top:20px;padding:16px;border-radius:12px;
    font-size:14px;display:none;text-align:center;
  }
  .status.loading{
    background:rgba(0,119,181,0.12);border:1px solid rgba(0,119,181,0.3);
    color:#7dd3fc;display:block;
  }
  .status.success{
    background:rgba(22,197,94,0.12);border:1px solid rgba(22,197,94,0.3);
    color:#4ade80;display:block;
  }
  .status.error{
    background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);
    color:#f87171;display:block;
  }
  .spinner{
    display:inline-block;width:14px;height:14px;
    border:2px solid rgba(125,211,252,0.3);
    border-top-color:#7dd3fc;border-radius:50%;
    animation:spin .7s linear infinite;margin-right:8px;vertical-align:middle;
  }
  @keyframes spin{to{transform:rotate(360deg)}}
  .success-icon{font-size:36px;margin-bottom:10px;display:block}
  .profile-card{
    background:rgba(22,197,94,0.08);border:1px solid rgba(22,197,94,0.25);
    border-radius:12px;padding:16px;margin-top:16px;text-align:left;
  }
  .profile-row{display:flex;align-items:center;gap:10px;margin-bottom:6px}
  .profile-label{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px}
  .profile-val{font-size:14px;color:#f1f5f9;font-weight:600}
  .note{font-size:12px;color:#475569;margin-top:24px;text-align:center;line-height:1.6}
  .note span{color:#0077b5}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">in</div>
    <div>
      <div class="logo-text">LinkedIn Connect</div>
      <div class="logo-sub">Video Factory — Auto Publisher</div>
    </div>
  </div>

  <h2>One-Click Connect</h2>
  <p class="subtitle">Apni LinkedIn email aur password dalein — bas!</p>

  <form id="connectForm" onsubmit="connect(event)">
    <label>LinkedIn Email</label>
    <input type="email" id="email" placeholder="aapki@email.com" required autocomplete="email"/>

    <label>Password</label>
    <input type="password" id="password" placeholder="••••••••••" required autocomplete="current-password"/>

    <button class="btn" id="btn" type="submit">
      🔗 &nbsp; Connect LinkedIn
    </button>
  </form>

  <div class="status" id="status"></div>
  <p class="note">🔒 Aapka password <span>sirf aapke computer</span> par use hota hai.<br>Koi server ya cloud pe store nahi hota.</p>
</div>

<script>
async function connect(e){
  e.preventDefault();
  const email    = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const btn      = document.getElementById('btn');
  const status   = document.getElementById('status');

  btn.disabled = true;
  status.className='status loading';
  status.innerHTML='<span class="spinner"></span> LinkedIn par login ho raha hai...';

  try{
    const res  = await fetch('/connect', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email, password})
    });
    const data = await res.json();

    if(data.success){
      status.className='status success';
      status.innerHTML=`
        <span class="success-icon">🎉</span>
        <strong>LinkedIn Connected!</strong>
        <div class="profile-card">
          <div class="profile-row">
            <div>
              <div class="profile-label">Name</div>
              <div class="profile-val">${data.name || '—'}</div>
            </div>
          </div>
          <div class="profile-label" style="margin-top:8px">URN</div>
          <div class="profile-val" style="font-size:12px;color:#94a3b8">${data.urn || '—'}</div>
        </div>
        <div style="margin-top:12px;font-size:13px;color:#4ade80">
          ✅ Auto-factory videos ab LinkedIn par post honge!
        </div>`;
      document.getElementById('connectForm').style.display='none';
    } else {
      status.className='status error';
      status.innerHTML=`❌ <strong>Error:</strong> ${data.error}`;
      btn.disabled=false;
    }
  } catch(err){
    status.className='status error';
    status.innerHTML=`❌ Server error: ${err.message}`;
    btn.disabled=false;
  }
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/connect", methods=["POST"])
def connect():
    data     = request.get_json()
    email    = (data.get("email")    or "").strip()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email aur password required hain!"})

    try:
        from linkedin_api import Linkedin
        print(f"[LinkedIn] Logging in as {email}...")
        api = Linkedin(email, password)

        # Fetch own profile
        profile = api.get_profile()
        first   = profile.get("firstName", {}).get("localized", {})
        last    = profile.get("lastName",  {}).get("localized", {})
        fname   = list(first.values())[0]  if first else ""
        lname   = list(last.values())[0]   if last  else ""
        name    = f"{fname} {lname}".strip() or email

        # Build person URN
        uid     = profile.get("entityUrn", "").split(":")[-1]
        urn     = f"urn:li:person:{uid}"

        # Extract session cookies for real API calls later
        cookies = {k: v for k, v in api.client.session.cookies.items()}

        # Save credentials
        creds = {
            "email":         email,
            "person_urn":    urn,
            "display_name":  name,
            "cookies":       cookies,
            # These are empty – we use cookie-based auth, no developer app needed
            "client_id":     "",
            "client_secret": "",
            "access_token":  "",
            "refresh_token": "",
        }
        with open(CREDS_FILE, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)

        print(f"[LinkedIn] ✅ Logged in! Name={name} URN={urn}")
        print(f"[LinkedIn] Credentials saved to: {CREDS_FILE}")

        return jsonify({"success": True, "name": name, "urn": urn})

    except Exception as ex:
        err_str = str(ex)
        print(f"[LinkedIn] ERROR: {err_str}")
        if "CHALLENGE" in err_str.upper() or "challenge" in err_str.lower():
            return jsonify({
                "success": False,
                "error": "LinkedIn ne security challenge maanga! Pehle browser mein linkedin.com par manual login karein, phir dobara try karein."
            })
        return jsonify({"success": False, "error": err_str})


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:9090")


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  LinkedIn One-Click Connect Tool")
    print("="*55)
    print("  Browser mein http://localhost:9090 open ho raha hai...")
    print("  Apni LinkedIn email + password dalein, bas!")
    print("  (Ctrl+C se band karein jab done ho)")
    print("="*55 + "\n")
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=9090, debug=False)
