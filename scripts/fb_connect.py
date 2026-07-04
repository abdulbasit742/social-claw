#!/usr/bin/env python3
"""
Facebook Direct Post Tool
==========================
Yeh tool Facebook Page par directly video/post karta hai.
Graph API Explorer se Page Access Token paste karein — bas!

Run: python scripts/fb_connect.py
Open: http://localhost:9091
"""
import os, sys, json, threading, webbrowser, time, secrets, requests
from flask import Flask, request, jsonify, render_template_string

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FB_CREDS = os.path.join(project_root, "fb_credentials.json")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def load_fb():
    try:
        if os.path.exists(FB_CREDS):
            with open(FB_CREDS) as f: return json.load(f)
    except: pass
    return {}

def save_fb(d):
    with open(FB_CREDS, "w") as f: json.dump(d, f, indent=2)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Facebook Connect — Video Factory</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{--bg:#0f1117;--s:#181c25;--s2:#1e2330;--b:rgba(255,255,255,.07);
  --t:#e8eaf0;--m:#5a6278;--fb:#1877f2;--ok:#22c55e}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--t);
  min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:36px 16px}

.top{width:100%;max-width:640px;display:flex;align-items:center;gap:10px;margin-bottom:32px}
.logo{width:34px;height:34px;border-radius:9px;background:var(--fb);
  display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:900;color:#fff}
.aname{font-size:15px;font-weight:700}

.card{width:100%;max-width:640px;background:var(--s);border:1px solid var(--b);
  border-radius:16px;padding:28px;margin-bottom:16px}
.card-title{font-size:16px;font-weight:700;color:#fff;margin-bottom:4px;display:flex;align-items:center;gap:8px}
.card-sub{font-size:13px;color:var(--m);margin-bottom:22px;line-height:1.6}

/* Steps */
.steps{display:flex;flex-direction:column;gap:14px;margin-bottom:22px}
.step{display:flex;gap:12px;align-items:flex-start}
.step-num{width:26px;height:26px;border-radius:50%;background:var(--fb);
  display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;
  color:#fff;flex-shrink:0;margin-top:1px}
.step-body{flex:1}
.step-title{font-size:14px;font-weight:600;color:#fff;margin-bottom:3px}
.step-desc{font-size:12px;color:var(--m);line-height:1.6}
.step-link{color:var(--fb);text-decoration:none;font-weight:600}
.step-link:hover{text-decoration:underline}

label{display:block;font-size:11px;font-weight:600;color:var(--m);
  text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
input,select,textarea{width:100%;padding:11px 14px;background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.08);border-radius:10px;color:#fff;font-size:13px;
  font-family:'Inter',sans-serif;outline:none;transition:.18s;margin-bottom:14px}
input:focus,select:focus,textarea:focus{border-color:var(--fb);box-shadow:0 0 0 3px rgba(24,119,242,.15)}
input::placeholder,textarea::placeholder{color:#2d3748}
select option{background:#1e2330}
textarea{resize:vertical;min-height:80px;margin-bottom:14px}

.btn{width:100%;padding:13px;border:none;border-radius:10px;color:#fff;font-size:14px;
  font-weight:700;cursor:pointer;font-family:'Inter',sans-serif;transition:.18s;
  display:flex;align-items:center;justify-content:center;gap:8px}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-fb{background:var(--fb);box-shadow:0 6px 18px rgba(24,119,242,.3)}
.btn-fb:hover:not(:disabled){background:#1565d8;transform:translateY(-1px);box-shadow:0 10px 24px rgba(24,119,242,.4)}
.btn-open{background:rgba(24,119,242,.12);color:var(--fb);border:1px solid rgba(24,119,242,.25)}
.btn-open:hover{background:rgba(24,119,242,.2)}

.stline{margin-top:12px;padding:12px 14px;border-radius:10px;font-size:13px;
  line-height:1.5;display:none}
.stline.loading{display:block;background:rgba(24,119,242,.08);color:#93c5fd;border:1px solid rgba(24,119,242,.2)}
.stline.success{display:block;background:rgba(34,197,94,.08);color:#4ade80;border:1px solid rgba(34,197,94,.2)}
.stline.error{display:block;background:rgba(239,68,68,.08);color:#f87171;border:1px solid rgba(239,68,68,.2)}
.spin{display:inline-block;width:11px;height:11px;border:2px solid rgba(147,197,253,.3);
  border-top-color:#93c5fd;border-radius:50%;animation:sp .7s linear infinite;margin-right:5px;vertical-align:middle}
@keyframes sp{to{transform:rotate(360deg)}}

.badge-ok{display:inline-block;background:rgba(34,197,94,.12);color:#4ade80;
  border:1px solid rgba(34,197,94,.2);border-radius:20px;padding:3px 12px;font-size:12px;font-weight:600}

.divider{border:none;border-top:1px solid var(--b);margin:20px 0}

.post-section{display:none}
.post-section.show{display:block}

.pages-list{display:flex;flex-direction:column;gap:8px;margin-bottom:16px}
.page-item{display:flex;align-items:center;gap:10px;padding:10px 12px;
  background:var(--s2);border:1px solid var(--b);border-radius:10px;cursor:pointer;transition:.15s}
.page-item:hover{border-color:var(--fb)}
.page-item.selected{border-color:var(--fb);background:rgba(24,119,242,.08)}
.page-icon{width:38px;height:38px;border-radius:50%;background:var(--fb);
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0}
.page-name{font-size:14px;font-weight:600;color:#fff}
.page-cat{font-size:12px;color:var(--m)}
</style>
</head>
<body>

<div class="top">
  <div class="logo">f</div>
  <div class="aname">Facebook Connect — Video Factory</div>
</div>

<!-- Step 1: Get Token -->
<div class="card" id="tokenCard">
  <div class="card-title">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="#1877f2"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
    Connect Facebook Page
  </div>
  <div class="card-sub">
    Facebook Graph API se Page Access Token lein — 2 minute mein post ready!
  </div>

  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-body">
        <div class="step-title">Graph API Explorer open karein</div>
        <div class="step-desc">
          <a class="step-link" href="#" onclick="openExplorer()">Graph API Explorer</a> → Login with Facebook → apna account select karein
        </div>
      </div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-body">
        <div class="step-title">Permissions add karein</div>
        <div class="step-desc">
          "Add a Permission" → <b>pages_show_list</b>, <b>pages_read_engagement</b>, <b>pages_manage_posts</b>, <b>publish_video</b> add karein
        </div>
      </div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div class="step-body">
        <div class="step-title">"Generate Access Token" click karein</div>
        <div class="step-desc">
          Popup mein "Allow" karein → Generated token neeche paste karein
        </div>
      </div>
    </div>
  </div>

  <button class="btn btn-open" onclick="openExplorer()" style="margin-bottom:16px">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M14 3h7v7h-2V6.41L10.41 15 9 13.59 17.59 5H14V3zM5 5h6v2H7v10h10v-4h2v6H5V5z"/></svg>
    Open Graph API Explorer
  </button>

  <label>User Access Token (Graph Explorer se copy karein)</label>
  <input type="text" id="userToken" placeholder="EAAxxxxxx... (paste here)"/>

  <button class="btn btn-fb" onclick="fetchPages()" id="fetchBtn">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
    Fetch My Pages
  </button>

  <div class="stline" id="tokenSt"></div>
</div>

<!-- Step 2: Select Page & Post -->
<div class="card post-section" id="postCard">
  <div class="card-title">&#10003;&nbsp; Select Page &amp; Post</div>
  <div class="card-sub" id="connectedAs"></div>

  <label>Your Facebook Pages</label>
  <div class="pages-list" id="pagesList"></div>

  <hr class="divider"/>

  <label>Post Caption / Message</label>
  <textarea id="postCaption" placeholder="Aapka video caption yahan likhein...&#10;&#10;#entrepreneurship #business #motivation"></textarea>

  <label>Video File Path</label>
  <input type="text" id="videoPath" placeholder="C:\Users\absh5\MoneyPrinterTurbo\storage\tasks\xxx\final.mp4"/>

  <button class="btn btn-fb" onclick="postToFacebook()" id="postBtn">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M2 12l10-9 10 9v9a1 1 0 01-1 1h-6v-5H9v5H3a1 1 0 01-1-1v-9z"/></svg>
    Post Video to Facebook Page
  </button>

  <div class="stline" id="postSt"></div>
</div>

<script>
let selectedPageId = '';
let selectedPageToken = '';

function openExplorer(){
  window.open('https://developers.facebook.com/tools/explorer/','_blank','width=900,height=700');
}

async function fetchPages(){
  const token = document.getElementById('userToken').value.trim();
  if(!token){setSt('tokenSt','error','Token paste karein!');return}
  const btn=document.getElementById('fetchBtn');
  btn.disabled=true;
  setSt('tokenSt','loading','Facebook pages fetch ho rahi hain...');
  const d = await post('/api/fb/pages',{token});
  if(d.success){
    setSt('tokenSt','success','Pages mili! Neeche select karein.');
    renderPages(d.pages, d.user_name);
    document.getElementById('postCard').classList.add('show');
  } else {
    setSt('tokenSt','error',d.error||'Error');
    btn.disabled=false;
  }
}

function renderPages(pages, userName){
  document.getElementById('connectedAs').textContent = 'Logged in as: '+userName+' — Ek page select karein';
  const list = document.getElementById('pagesList');
  list.innerHTML = '';
  pages.forEach(p => {
    const div = document.createElement('div');
    div.className = 'page-item';
    div.innerHTML = `<div class="page-icon">${p.name.charAt(0).toUpperCase()}</div>
      <div><div class="page-name">${p.name}</div><div class="page-cat">${p.category||'Page'} · ID: ${p.id}</div></div>`;
    div.onclick = () => {
      document.querySelectorAll('.page-item').forEach(x=>x.classList.remove('selected'));
      div.classList.add('selected');
      selectedPageId = p.id;
      selectedPageToken = p.access_token;
    };
    list.appendChild(div);
  });
  if(pages.length===1){
    list.firstChild.click();
  }
}

async function postToFacebook(){
  if(!selectedPageId){alert('Pehle ek page select karein!');return}
  const caption = document.getElementById('postCaption').value.trim();
  const videoPath = document.getElementById('videoPath').value.trim();
  if(!videoPath){alert('Video file path dalein!');return}

  const btn=document.getElementById('postBtn');
  btn.disabled=true;
  setSt('postSt','loading','Facebook par video upload ho rahi hai — kuch minute lag sakte hain...');

  const d = await post('/api/fb/post_video',{
    page_id: selectedPageId,
    page_token: selectedPageToken,
    caption: caption,
    video_path: videoPath
  });

  if(d.success){
    setSt('postSt','success',
      'Video posted! <a href="'+d.url+'" target="_blank" style="color:#4ade80;font-weight:700">Facebook par dekhein &#8599;</a>');
  } else {
    setSt('postSt','error','Error: '+d.error);
    btn.disabled=false;
  }
}

function setSt(id,cls,html){
  const el=document.getElementById(id);
  el.className='stline '+cls;
  el.innerHTML=(cls==='loading'?'<span class="spin"></span>':'')+html;
}
async function post(url,body){
  try{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
  catch(e){return{success:false,error:e.message}}
}
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/fb/pages", methods=["POST"])
def fb_pages():
    d     = request.get_json()
    token = (d.get("token") or "").strip()
    if not token:
        return jsonify({"success":False,"error":"Token nahi mila!"})
    try:
        PROXIES = {"http":"http://172.30.10.10:3128","https":"http://172.30.10.10:3128"}
        # Get user info
        me = requests.get("https://graph.facebook.com/v20.0/me",
            params={"access_token":token,"fields":"id,name"},
            proxies=PROXIES, timeout=20)
        me.raise_for_status()
        me_d = me.json()
        user_name = me_d.get("name","Unknown")

        # Get pages
        pages_r = requests.get("https://graph.facebook.com/v20.0/me/accounts",
            params={"access_token":token,"fields":"id,name,category,access_token"},
            proxies=PROXIES, timeout=20)
        pages_r.raise_for_status()
        pages_d = pages_r.json()
        pages   = pages_d.get("data",[])

        if not pages:
            return jsonify({"success":False,"error":"Aapke account mein koi Facebook Page nahi mili! Pehle ek Page create karein."})

        # Save user token
        creds = load_fb()
        creds["user_token"]  = token
        creds["user_name"]   = user_name
        creds["pages"]       = pages
        save_fb(creds)
        print(f"[Facebook] {user_name} — {len(pages)} pages found")
        return jsonify({"success":True,"user_name":user_name,"pages":pages})
    except Exception as ex:
        err = str(ex)
        print(f"[Facebook] pages error: {err}")
        if "368" in err or "security" in err.lower():
            err = "Facebook security lock active hai. 24-48 ghante baad retry karein, ya dusre account ka token use karein."
        return jsonify({"success":False,"error":err})

@app.route("/api/fb/post_video", methods=["POST"])
def fb_post_video():
    d           = request.get_json()
    page_id     = d.get("page_id","")
    page_token  = d.get("page_token","")
    caption     = d.get("caption","")
    video_path  = d.get("video_path","")

    if not all([page_id, page_token, video_path]):
        return jsonify({"success":False,"error":"Page, token aur video path required hain!"})
    if not os.path.exists(video_path):
        return jsonify({"success":False,"error":f"Video file nahi mili: {video_path}"})

    PROXIES = {"http":"http://172.30.10.10:3128","https":"http://172.30.10.10:3128"}

    try:
        file_size = os.path.getsize(video_path)
        print(f"[Facebook] Uploading {os.path.basename(video_path)} ({file_size//1024//1024}MB) to page {page_id}")

        # Step 1: Initialize resumable upload session
        init_url  = f"https://graph.facebook.com/v20.0/{page_id}/videos"
        init_data = {
            "upload_phase": "start",
            "file_size":    file_size,
            "access_token": page_token,
        }
        init_r = requests.post(init_url, data=init_data, proxies=PROXIES, timeout=30)
        init_r.raise_for_status()
        init_d   = init_r.json()
        upload_session_id = init_d.get("upload_session_id")
        video_id          = init_d.get("video_id")
        start_offset      = int(init_d.get("start_offset", 0))

        print(f"[Facebook] Upload session: {upload_session_id} | video_id: {video_id}")

        # Step 2: Transfer chunks
        CHUNK = 10 * 1024 * 1024  # 10MB
        with open(video_path, "rb") as vf:
            while True:
                vf.seek(start_offset)
                chunk = vf.read(CHUNK)
                if not chunk:
                    break
                trans_r = requests.post(init_url,
                    data={"upload_phase":"transfer","upload_session_id":upload_session_id,
                          "start_offset":start_offset,"access_token":page_token},
                    files={"video_file_chunk":("chunk.mp4", chunk, "video/mp4")},
                    proxies=PROXIES, timeout=120)
                trans_r.raise_for_status()
                td = trans_r.json()
                next_offset = int(td.get("start_offset", start_offset + len(chunk)))
                print(f"[Facebook] Chunk uploaded: {next_offset}/{file_size}")
                if next_offset >= file_size or next_offset == start_offset:
                    break
                start_offset = next_offset

        # Step 3: Finish
        finish_r = requests.post(init_url,
            data={"upload_phase":"finish","upload_session_id":upload_session_id,
                  "description":caption,"access_token":page_token,"published":"true"},
            proxies=PROXIES, timeout=60)
        finish_r.raise_for_status()
        finish_d = finish_r.json()

        if finish_d.get("success") or finish_d.get("id"):
            vid_id = finish_d.get("id") or video_id
            url    = f"https://www.facebook.com/{page_id}/videos/{vid_id}"
            creds  = load_fb()
            creds["last_post"] = {"video_id":vid_id,"url":url,"caption":caption}
            save_fb(creds)
            print(f"[Facebook] Posted! {url}")
            return jsonify({"success":True,"video_id":vid_id,"url":url})
        else:
            return jsonify({"success":False,"error":str(finish_d)})

    except Exception as ex:
        err = str(ex)
        print(f"[Facebook] post error: {err}")
        if "368" in err:
            err = "Facebook account par security restriction hai. 24-48 ghante baad retry karein."
        elif "190" in err:
            err = "Token expired! Graph Explorer se naya token generate karein."
        return jsonify({"success":False,"error":err})

if __name__=="__main__":
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    print("="*52)
    print("  Facebook Direct Post Tool")
    print("  http://localhost:9091")
    print("="*52)
    threading.Thread(target=lambda:(time.sleep(1.5),webbrowser.open("http://localhost:9091")),daemon=True).start()
    app.run(host="127.0.0.1",port=9091,debug=False)
