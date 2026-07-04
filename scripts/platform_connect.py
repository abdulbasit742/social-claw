#!/usr/bin/env python3
"""
Video Factory — Platform Connect Portal
One-click Google OAuth + LinkedIn — No external files needed
"""
import os, sys, json, threading, webbrowser, time, secrets
from flask import Flask, request, jsonify, render_template_string

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

LINKEDIN_CREDS = os.path.join(project_root, "linkedin_credentials.json")
YT_CREDS       = os.path.join(project_root, "yt_credentials.json")
YT_CLIENT_FILE = os.path.join(project_root, "client_secrets.json")
OAUTH_CFG_FILE = os.path.join(project_root, "google_oauth_app.json")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

_yt_result = {"done":False,"success":False,"error":"","channel_name":"","channel_id":""}
_yt_flow   = None

# ── Load saved Google OAuth app config ─────────────────────────
def load_google_app():
    if os.path.exists(OAUTH_CFG_FILE):
        try:
            with open(OAUTH_CFG_FILE) as f:
                return json.load(f)
        except: pass
    return {}

def has_google_app():
    d = load_google_app()
    return bool(d.get("client_id") and d.get("client_secret"))

def yt_already_connected():
    if not os.path.exists(YT_CREDS): return None
    try:
        with open(YT_CREDS) as f: d = json.load(f)
        if d.get("access_token"): return d.get("channel_name","Connected")
    except: pass
    return None

def li_already_connected():
    if not os.path.exists(LINKEDIN_CREDS): return None
    try:
        with open(LINKEDIN_CREDS) as f: d = json.load(f)
        if d.get("person_urn"): return d.get("display_name","Connected")
    except: pass
    return None

# ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Video Factory · Connect Accounts</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{--bg:#0f1117;--surface:#181c25;--surface2:#1e2330;--border:rgba(255,255,255,0.07);
  --text:#e8eaf0;--muted:#5a6278;--accent:#5865f2;--green:#22c55e;--red:#ef4444}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);
  min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:36px 16px}

/* ── Topbar ── */
.top{width:100%;max-width:680px;display:flex;align-items:center;gap:10px;margin-bottom:36px}
.logo{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#5865f2,#a78bfa);
  display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:#fff}
.app-name{font-size:15px;font-weight:700}
.app-sub{font-size:12px;color:var(--muted);margin-left:auto}

/* ── Setup Banner ── */
.setup-banner{
  width:100%;max-width:680px;margin-bottom:20px;
  background:linear-gradient(135deg,rgba(88,101,242,.12),rgba(167,139,250,.08));
  border:1px solid rgba(88,101,242,.25);border-radius:14px;padding:18px 20px;
  display:none;
}
.setup-banner.show{display:block}
.sb-title{font-size:14px;font-weight:700;color:#a5b4fc;margin-bottom:6px}
.sb-desc{font-size:12px;color:var(--muted);line-height:1.6;margin-bottom:14px}
.sb-fields{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
@media(max-width:500px){.sb-fields{grid-template-columns:1fr}}
.sb-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;display:block}
.sb-input{width:100%;padding:10px 12px;background:rgba(255,255,255,0.05);
  border:1px solid rgba(255,255,255,0.09);border-radius:8px;color:#fff;font-size:12px;
  font-family:'Inter',sans-serif;outline:none;transition:.18s;}
.sb-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(88,101,242,.15)}
.sb-input::placeholder{color:#334155}
.sb-row{display:flex;gap:8px}
.btn-setup{padding:9px 18px;border:none;border-radius:8px;
  background:linear-gradient(135deg,#5865f2,#7c3aed);color:#fff;
  font-size:13px;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif;
  transition:.18s;white-space:nowrap}
.btn-setup:hover{transform:translateY(-1px);box-shadow:0 6px 16px rgba(88,101,242,.35)}
.btn-open-gcloud{padding:9px 18px;border:1px solid rgba(255,255,255,.1);border-radius:8px;
  background:transparent;color:var(--muted);
  font-size:12px;font-weight:500;cursor:pointer;font-family:'Inter',sans-serif;transition:.18s}
.btn-open-gcloud:hover{color:var(--text);border-color:rgba(255,255,255,.2)}

/* ── Page head ── */
.ph{width:100%;max-width:680px;margin-bottom:22px}
.ph h1{font-size:22px;font-weight:700;color:#fff;margin-bottom:4px}
.ph p{font-size:13px;color:var(--muted)}

/* ── List ── */
.list{width:100%;max-width:680px;display:flex;flex-direction:column;gap:8px}

/* ── Row ── */
.row{background:var(--surface);border:1px solid var(--border);border-radius:13px;
  padding:16px 18px;transition:border-color .2s}
.row:hover{border-color:rgba(255,255,255,.12)}
.row-main{display:flex;align-items:center;gap:14px}
.picon{width:42px;height:42px;border-radius:11px;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;color:#fff;font-size:17px;font-weight:900}
.picon.li{background:linear-gradient(135deg,#0077b5,#00a0dc)}
.picon.yt{background:linear-gradient(135deg,#ff0000,#ff4444)}
.picon.ig{background:linear-gradient(135deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)}
.picon.tk{background:#010101}
.picon.tg{background:#2aabee}
.picon.xx{background:#010101;font-size:14px}
.rb{flex:1;min-width:0}
.rname{font-size:14px;font-weight:600;color:#fff}
.rdesc{font-size:12px;color:var(--muted);margin-top:1px}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:500;
  padding:3px 9px;border-radius:20px;flex-shrink:0}
.badge.ok{background:rgba(34,197,94,.1);color:#4ade80;border:1px solid rgba(34,197,94,.2)}
.badge.no{background:rgba(90,98,120,.1);color:var(--muted);border:1px solid rgba(90,98,120,.2)}
.badge.busy{background:rgba(251,191,36,.1);color:#fbbf24;border:1px solid rgba(251,191,36,.2)}

/* ── Buttons ── */
.btn{flex-shrink:0;padding:8px 16px;border-radius:8px;border:none;font-size:12px;
  font-weight:600;cursor:pointer;font-family:'Inter',sans-serif;transition:all .18s;
  display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none!important}
.btn-google{background:#fff;color:#3c4043;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.btn-google:hover:not(:disabled){background:#f5f5f5;box-shadow:0 3px 8px rgba(0,0,0,.2);transform:translateY(-1px)}
.btn-blue{background:#0077b5;color:#fff}
.btn-blue:hover:not(:disabled){background:#0088cc;transform:translateY(-1px)}
.btn-dim{background:rgba(255,255,255,.05);color:var(--muted);border:1px solid var(--border)}
.btn-dim:hover:not(:disabled){background:rgba(255,255,255,.09);color:var(--text)}
.glogo{width:15px;height:15px;flex-shrink:0}

/* ── Inline form ── */
.iform{display:none;margin-top:14px;padding:14px;
  background:var(--surface2);border:1px solid var(--border);border-radius:10px}
.iform.open{display:block}
.iflabel{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:4px;display:block}
.ifinput{width:100%;padding:9px 12px;background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.08);border-radius:8px;color:#fff;font-size:13px;
  font-family:'Inter',sans-serif;outline:none;transition:.18s;margin-bottom:10px}
.ifinput:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(88,101,242,.12)}
.ifinput::placeholder{color:#2d3748}
.form-btns{display:flex;gap:8px;flex-wrap:wrap}

/* ── Status ── */
.stline{margin-top:10px;padding:9px 12px;border-radius:8px;font-size:12px;
  line-height:1.5;display:none}
.stline.loading{display:block;background:rgba(88,101,242,.07);color:#a5b4fc;border:1px solid rgba(88,101,242,.18)}
.stline.success{display:block;background:rgba(34,197,94,.07);color:#4ade80;border:1px solid rgba(34,197,94,.18)}
.stline.error{display:block;background:rgba(239,68,68,.07);color:#f87171;border:1px solid rgba(239,68,68,.18)}
.stline.info{display:block;background:rgba(59,130,246,.07);color:#93c5fd;border:1px solid rgba(59,130,246,.18)}
.spin{display:inline-block;width:10px;height:10px;border:2px solid rgba(165,180,252,.3);
  border-top-color:#a5b4fc;border-radius:50%;animation:sp .7s linear infinite;margin-right:4px;vertical-align:middle}
@keyframes sp{to{transform:rotate(360deg)}}

.footer{margin-top:36px;font-size:11px;color:#1e2330;text-align:center}
</style>
</head>
<body>

<!-- Topbar -->
<div class="top">
  <div class="logo">VF</div>
  <div class="app-name">Video Factory</div>
  <div class="app-sub">Social Accounts</div>
</div>

<!-- Google App Setup Banner -->
<div class="setup-banner {{ 'show' if not has_app else '' }}" id="setupBanner">
  <div class="sb-title">&#9889; Google OAuth App Setup</div>
  <div class="sb-desc">
    "Sign in with Google" ke liye apna Google Cloud OAuth app setup karein.<br>
    <b>Sirf ek baar karna hai</b> — phir YouTube aur future platforms automatically connect honge.
  </div>
  <div class="sb-fields">
    <div>
      <span class="sb-label">Client ID</span>
      <input class="sb-input" id="gClientId" placeholder="xxxxx.apps.googleusercontent.com"/>
    </div>
    <div>
      <span class="sb-label">Client Secret</span>
      <input class="sb-input" id="gClientSecret" placeholder="GOCSPX-..."/>
    </div>
  </div>
  <div class="sb-row">
    <button class="btn-setup" onclick="saveGoogleApp()">Save &amp; Enable Google Sign-In</button>
    <button class="btn-open-gcloud" onclick="openGCloud()">&#8599; Open Google Cloud Console</button>
  </div>
  <div class="stline" id="setupSt" style="margin-top:10px"></div>
  <div style="margin-top:12px;font-size:11px;color:#334155;line-height:1.7">
    Google Cloud Console &rarr; APIs &amp; Services &rarr; Credentials &rarr; Create OAuth 2.0 Client ID<br>
    Application type: <b>Desktop app</b> &rarr; Create &rarr; Client ID aur Secret copy karein
  </div>
</div>

<!-- Page heading -->
<div class="ph">
  <h1>Connect Social Accounts</h1>
  <p>Ek baar connect karein — Videos automatically post honge</p>
</div>

<!-- Account list -->
<div class="list">

  <!-- YouTube -->
  <div class="row" id="ytRow">
    <div class="row-main">
      <div class="picon yt">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="white"><path d="M21.8 8s-.2-1.4-.8-2c-.8-.8-1.7-.8-2.1-.9C16.3 5 12 5 12 5s-4.3 0-6.9.1c-.4.1-1.3.1-2.1.9-.6.6-.8 2-.8 2S2 9.6 2 11.2v1.5c0 1.6.2 3.2.2 3.2s.2 1.4.8 2c.8.8 1.8.8 2.3.8C6.8 19 12 19 12 19s4.3 0 6.9-.1c.4-.1 1.3-.1 2.1-.9.6-.6.8-2 .8-2S22 14.4 22 12.8v-1.5C22 9.6 21.8 8 21.8 8zM10 15V9l6 3-6 3z"/></svg>
      </div>
      <div class="rb">
        <div class="rname">YouTube</div>
        <div class="rdesc" id="ytDesc">{{ yt_name or 'Google account se connect karein' }}</div>
      </div>
      <span class="badge {{ 'ok' if yt_name else 'no' }}" id="ytBadge">{{ yt_name or 'Not connected' }}</span>
      {% if not yt_name %}
      <button class="btn btn-google" id="ytBtn" onclick="connectYouTube()" {{ 'disabled' if not has_app else '' }} title="{{ 'Pehle Google App setup karein (upar)' if not has_app else '' }}">
        <svg class="glogo" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.9 2.5 30.3 0 24 0 14.8 0 6.9 5.4 3 13.3l7.8 6C12.7 13.2 17.9 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10 7.1-17z"/><path fill="#FBBC05" d="M10.8 28.7A14.5 14.5 0 019.5 24c0-1.6.3-3.2.8-4.7L2.5 13.3A23.9 23.9 0 000 24c0 3.8.9 7.4 2.5 10.6l8.3-5.9z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.2 1.5-4.9 2.3-8.4 2.3-6.1 0-11.3-3.7-13.2-9l-7.8 6A24 24 0 0024 48z"/></svg>
        Sign in with Google
      </button>
      {% else %}
      <button class="btn btn-dim" disabled>Connected</button>
      {% endif %}
    </div>
    <div class="stline" id="ytSt"></div>
  </div>

  <!-- LinkedIn -->
  <div class="row" id="liRow">
    <div class="row-main">
      <div class="picon li">in</div>
      <div class="rb">
        <div class="rname">LinkedIn</div>
        <div class="rdesc" id="liDesc">{{ li_name or 'Email + Password — 1 click' }}</div>
      </div>
      <span class="badge {{ 'ok' if li_name else 'no' }}" id="liBadge">{{ li_name or 'Not connected' }}</span>
      {% if not li_name %}
      <button class="btn btn-blue" id="liBtn" onclick="toggleLi()">Connect</button>
      {% else %}
      <button class="btn btn-dim" disabled>Connected</button>
      {% endif %}
    </div>
    {% if not li_name %}
    <div class="iform" id="liForm">
      <label class="iflabel">Email</label>
      <input class="ifinput" type="email" id="liEmail" placeholder="linkedin@email.com" autocomplete="email"/>
      <label class="iflabel">Password</label>
      <input class="ifinput" type="password" id="liPass" placeholder="••••••••" autocomplete="current-password"/>
      <div class="form-btns">
        <button class="btn btn-blue" onclick="connectLinkedIn()" id="liSub">Connect LinkedIn</button>
        <button class="btn btn-dim" onclick="toggleLi()">Cancel</button>
      </div>
      <div class="stline" id="liSt"></div>
    </div>
    {% endif %}
  </div>

  <!-- Instagram -->
  <div class="row">
    <div class="row-main">
      <div class="picon ig">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="white"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
      </div>
      <div class="rb"><div class="rname">Instagram</div><div class="rdesc">Reels auto-post (instagrapi)</div></div>
      <span class="badge ok">Connected</span>
      <button class="btn btn-dim" disabled>Active</button>
    </div>
  </div>

  <!-- TikTok -->
  <div class="row">
    <div class="row-main">
      <div class="picon tk">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="white"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.32 6.32 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.18 8.18 0 004.78 1.52V6.77a4.85 4.85 0 01-1-.08z"/></svg>
      </div>
      <div class="rb"><div class="rname">TikTok</div><div class="rdesc">Developer sandbox — OAuth pending</div></div>
      <span class="badge no">Not connected</span>
      <button class="btn btn-dim" onclick="alert('TikTok: Developer portal se Client Key + Secret lain.')">Setup</button>
    </div>
  </div>

  <!-- Telegram -->
  <div class="row">
    <div class="row-main">
      <div class="picon tg">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="white"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
      </div>
      <div class="rb"><div class="rname">Telegram</div><div class="rdesc">Bot token configured</div></div>
      <span class="badge ok">Connected</span>
      <button class="btn btn-dim" disabled>Active</button>
    </div>
  </div>

  <!-- Twitter/X -->
  <div class="row">
    <div class="row-main">
      <div class="picon xx">&#120143;</div>
      <div class="rb"><div class="rname">Twitter / X</div><div class="rdesc">API v2 keys needed</div></div>
      <span class="badge no">Not connected</span>
      <button class="btn btn-dim" onclick="alert('Twitter: developer.x.com se API Key + Secret + Access Tokens lain.')">Setup</button>
    </div>
  </div>

</div>
<div class="footer">Video Factory &mdash; All credentials stored locally on your PC only</div>

<script>
const HAS_APP = {{ 'true' if has_app else 'false' }};

/* ── Google App Setup ─────────────────────────────────── */
function openGCloud(){
  window.open('https://console.cloud.google.com/apis/credentials','_blank');
}
async function saveGoogleApp(){
  const cid  = document.getElementById('gClientId').value.trim();
  const csec = document.getElementById('gClientSecret').value.trim();
  if(!cid||!csec){setSt('setupSt','error','Client ID aur Secret dono fill karein!');return}
  const d=await post('/api/setup_google',{client_id:cid,client_secret:csec});
  if(d.success){
    setSt('setupSt','success','Google App saved! Ab "Sign in with Google" button active hai. Page refresh ho raha hai...');
    setTimeout(()=>location.reload(),1800);
  } else {
    setSt('setupSt','error',d.error||'Error');
  }
}

/* ── YouTube ──────────────────────────────────────────── */
async function connectYouTube(){
  const btn=document.getElementById('ytBtn');
  btn.disabled=true;
  setSt('ytSt','loading','Google login popup khul raha hai...');
  const d=await post('/api/youtube/start',{});
  if(d.success && d.auth_url){
    setSt('ytSt','info','Google window mein login karein aur Allow dabao.<br><small><a href="'+d.auth_url+'" target="_blank" style="color:#60a5fa">Auto-open na ho to yahan click karein</a></small>');
    window.open(d.auth_url,'_blank','width=500,height=620,left=300,top=80');
    pollYT();
  } else {
    setSt('ytSt','error',d.error||'Unknown');
    btn.disabled=false;
  }
}
async function pollYT(){
  for(let i=0;i<120;i++){
    await sleep(2500);
    const d=await get('/api/youtube/status');
    if(d.done){
      if(d.success){
        document.getElementById('ytBadge').className='badge ok';
        document.getElementById('ytBadge').textContent=d.channel_name;
        document.getElementById('ytDesc').textContent='Connected: '+d.channel_name;
        document.getElementById('ytBtn').style.display='none';
        setSt('ytSt','success','YouTube connected! Channel: '+d.channel_name);
      } else { setSt('ytSt','error',d.error||'Error'); document.getElementById('ytBtn').disabled=false; }
      return;
    }
  }
  setSt('ytSt','error','Timeout — retry karein');
  document.getElementById('ytBtn').disabled=false;
}

/* ── LinkedIn ─────────────────────────────────────────── */
function toggleLi(){document.getElementById('liForm').classList.toggle('open')}
async function connectLinkedIn(){
  const email=document.getElementById('liEmail').value.trim();
  const pass =document.getElementById('liPass').value;
  if(!email||!pass){alert('Email aur password dalein!');return}
  const sub=document.getElementById('liSub'); sub.disabled=true;
  setSt('liSt','loading','LinkedIn par login ho raha hai...');
  const d=await post('/api/linkedin',{email,password:pass});
  if(d.success){
    document.getElementById('liForm').classList.remove('open');
    document.getElementById('liBadge').className='badge ok';
    document.getElementById('liBadge').textContent=d.name;
    document.getElementById('liDesc').textContent='Connected: '+d.name;
    document.getElementById('liBtn').style.display='none';
    setSt('liSt','success','LinkedIn connected! Welcom, '+d.name);
  } else { setSt('liSt','error',d.error||'Error'); sub.disabled=false; }
}

/* ── Utils ────────────────────────────────────────────── */
function setSt(id,cls,html){
  const el=document.getElementById(id);
  el.className='stline '+cls;
  el.innerHTML=(cls==='loading'?'<span class="spin"></span>':'')+html;
}
async function post(url,body){
  try{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
  catch(e){return{success:false,error:e.message}}
}
async function get(url){try{const r=await fetch(url);return r.json()}catch(e){return{}}}
function sleep(ms){return new Promise(r=>setTimeout(r,ms))}
</script>
</body>
</html>"""

# ── Routes ────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML,
        has_app=has_google_app(),
        yt_name=yt_already_connected(),
        li_name=li_already_connected())

@app.route("/api/setup_google", methods=["POST"])
def setup_google():
    d   = request.get_json()
    cid = (d.get("client_id")     or "").strip()
    cs  = (d.get("client_secret") or "").strip()
    if not cid or not cs:
        return jsonify({"success":False,"error":"Dono fields fill karein!"})
    cfg = {"client_id":cid,"client_secret":cs,
           "auth_uri":"https://accounts.google.com/o/oauth2/auth",
           "token_uri":"https://oauth2.googleapis.com/token"}
    with open(OAUTH_CFG_FILE,"w") as f: json.dump(cfg,f,indent=2)
    # Also create client_secrets.json format
    cs_json = {"installed":{"client_id":cid,"client_secret":cs,
        "auth_uri":cfg["auth_uri"],"token_uri":cfg["token_uri"],
        "redirect_uris":["http://localhost:9090/oauth2callback"]}}
    with open(YT_CLIENT_FILE,"w") as f: json.dump(cs_json,f,indent=2)
    print(f"[Setup] Google OAuth App saved: {cid[:20]}...")
    return jsonify({"success":True})

@app.route("/api/youtube/start", methods=["POST"])
def yt_start():
    global _yt_flow, _yt_result
    _yt_result={"done":False,"success":False,"error":"","channel_name":"","channel_id":""}
    app_cfg = load_google_app()
    cid  = app_cfg.get("client_id","")
    csec = app_cfg.get("client_secret","")
    if not cid:
        return jsonify({"success":False,"error":"Pehle Google OAuth App setup karein (upar banner mein)!"})
    try:
        from google_auth_oauthlib.flow import Flow
        SCOPES=["https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly"]
        REDIR="http://localhost:9090/oauth2callback"
        cfg={"installed":{"client_id":cid,"client_secret":csec,
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token","redirect_uris":[REDIR]}}
        flow=Flow.from_client_config(cfg,scopes=SCOPES,redirect_uri=REDIR)
        _yt_flow=flow
        url,_=flow.authorization_url(prompt="consent",access_type="offline")
        return jsonify({"success":True,"auth_url":url})
    except Exception as ex:
        return jsonify({"success":False,"error":str(ex)})

@app.route("/oauth2callback")
def yt_cb():
    global _yt_flow,_yt_result
    try:
        code=request.args.get("code")
        if not code:
            _yt_result={"done":True,"success":False,"error":"No code"}
            return "<h2 style='color:red'>No code!</h2>"
        _yt_flow.fetch_token(code=code)
        cr=_yt_flow.credentials
        from googleapiclient.discovery import build
        yt=build("youtube","v3",credentials=cr)
        ch=yt.channels().list(part="snippet",mine=True).execute()
        cid=ch["items"][0]["id"]; name=ch["items"][0]["snippet"]["title"]
        app_cfg=load_google_app()
        td={"client_id":app_cfg.get("client_id",cr.client_id),
            "client_secret":app_cfg.get("client_secret",cr.client_secret),
            "access_token":cr.token,"refresh_token":cr.refresh_token,
            "token_uri":cr.token_uri,"scopes":list(cr.scopes or []),
            "channel_id":cid,"channel_name":name}
        with open(YT_CREDS,"w") as f: json.dump(td,f,indent=2)
        _yt_result={"done":True,"success":True,"channel_name":name,"channel_id":cid}
        print(f"[YouTube] {name} ({cid})")
        return """<html><head><style>body{font-family:Inter,sans-serif;background:#0f1117;color:#4ade80;
        display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;margin:0;
        font-size:18px}div{padding:40px}</style></head>
        <body><div><div style="font-size:64px;margin-bottom:16px">&#10003;</div>
        <b>YouTube Connected!</b><br><span style="color:#5a6278;font-size:14px;margin-top:8px;display:block">
        Yeh window band kar sakte hain.</span></div></body></html>"""
    except Exception as ex:
        _yt_result={"done":True,"success":False,"error":str(ex)}
        return f"<h2 style='color:red'>Error: {ex}</h2>"

@app.route("/api/youtube/status")
def yt_st(): return jsonify(_yt_result)

@app.route("/api/linkedin", methods=["POST"])
def api_linkedin():
    d=request.get_json()
    email=(d.get("email") or "").strip()
    pwd=(d.get("password") or "").strip()
    if not email or not pwd:
        return jsonify({"success":False,"error":"Email aur password dalein!"})
    try:
        from linkedin_api import Linkedin
        print(f"[LinkedIn] Login: {email}")
        api=Linkedin(email,pwd)
        prof=api.get_profile()
        first=list((prof.get("firstName",{}).get("localized",{})).values())
        last =list((prof.get("lastName", {}).get("localized",{})).values())
        name=f"{first[0] if first else ''} {last[0] if last else ''}".strip() or email
        uid=prof.get("entityUrn","").split(":")[-1]
        urn=f"urn:li:person:{uid}"
        cookies={k:v for k,v in api.client.session.cookies.items()}
        creds={"email":email,"person_urn":urn,"display_name":name,
               "cookies":cookies,"client_id":"","client_secret":"",
               "access_token":"","refresh_token":""}
        with open(LINKEDIN_CREDS,"w",encoding="utf-8") as f: json.dump(creds,f,indent=2)
        print(f"[LinkedIn] OK  {name}")
        return jsonify({"success":True,"name":name,"urn":urn})
    except Exception as ex:
        err=str(ex)
        if "CHALLENGE" in err.upper():
            err="Security challenge! Pehle browser mein linkedin.com par login karein, phir retry."
        return jsonify({"success":False,"error":err})

if __name__=="__main__":
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    print("="*50)
    print("  Video Factory - Platform Connect Portal")
    print("  http://localhost:9090")
    print("="*50)
    threading.Thread(target=lambda:(time.sleep(1.5),webbrowser.open("http://localhost:9090")),daemon=True).start()
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"]="1"
    app.run(host="127.0.0.1",port=9090,debug=False)
