"""
tech_factory.py — Autonomous AI/Tech Content Factory
Inspired by @satyamtechinsights (387K followers, 675 posts)

This runs as a SEPARATE daemon alongside auto_factory.py.
Niche: AI Tools, Machine Learning, ChatGPT, Coding, Tech Breakthroughs
Style: Hook → Problem → AI Solution → Actionable Tip → CTA
Target: Instagram Reels, TikTok, YouTube Shorts, LinkedIn, Facebook
"""

import os
import sys
import json
import time
import logging
import urllib.request
import subprocess
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------------------------------------------------------------
# Path Setup
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ["NO_PROXY"]    = "localhost,127.0.0.1"
os.environ["no_proxy"]    = "localhost,127.0.0.1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/tech_factory.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logging.SUCCESS = 25
logging.addLevelName(logging.SUCCESS, "SUCCESS")
def _success(msg, *args, **kwargs):
    logging.log(logging.SUCCESS, msg, *args, **kwargs)
logging.success = _success

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
TECH_CONFIG_PATH  = "tech_factory.config.json"
TECH_TOPICS_PATH  = "scripts/tech_topics.json"
TECH_DONE_PATH    = "scripts/tech_done.json"
PYTHON_EXE        = r"C:\Users\absh5\MoneyPrinterTurbo\venv\Scripts\python.exe"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ProcessLock:
    def __init__(self, filepath):
        self.filepath = filepath
        self.acquired = False

    def __enter__(self):
        start_time = time.time()
        while time.time() - start_time < 1200:
            try:
                fd = os.open(self.filepath, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self.acquired = True
                return self
            except FileExistsError:
                time.sleep(5)
        try:
            mtime = os.path.getmtime(self.filepath)
            if time.time() - mtime > 900:
                try:
                    os.remove(self.filepath)
                except Exception:
                    pass
                fd = os.open(self.filepath, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self.acquired = True
                return self
        except Exception:
            pass
        raise TimeoutError("Failed to acquire cross-process upload lock within 20 minutes.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            try:
                os.remove(self.filepath)
            except Exception:
                pass
            self.acquired = False

upload_lock   = ProcessLock(os.path.join(PROJECT_ROOT, "upload.lock"))
queue_lock    = threading.Lock()
done_log_lock = threading.Lock()

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load {path}: {e}")
        return {}

def save_json(path, data):
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Failed to save {path}: {e}")

def call_ollama(prompt, json_mode=False):
    url  = "http://127.0.0.1:11434/api/generate"
    data = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False}
    if json_mode:
        data["format"] = "json"
    req_data = json.dumps(data).encode("utf-8")
    proxy    = urllib.request.ProxyHandler({})
    opener   = urllib.request.build_opener(proxy)
    req      = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
    for i in range(3):
        try:
            with opener.open(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8")).get("response", "").strip()
        except Exception as e:
            logging.warning(f"Ollama attempt {i+1} failed: {e}")
            if i < 2:
                time.sleep(5)
    raise ConnectionError("Ollama unreachable after 3 attempts.")

# ------------------------------------------------------------------
# Script Generator — SatyamTechInsights style
# ------------------------------------------------------------------

def generate_tech_script(topic):
    logging.info(f"[Tech] Generating script for '{topic}'...")
    prompt = f"""You are a viral AI/tech content creator with 387K Instagram followers.
Your style is exactly like @satyamtechinsights — educational, exciting, beginner-friendly.

Write a short-form video script (YouTube Shorts / Instagram Reels / TikTok) for:
"{topic}"

STRICT RULES:
- Word count: 100-160 words ONLY
- No narrator labels, no stage directions, no headers
- Pure spoken words only
- Short, punchy sentences and ellipses (...) for natural pacing

STRUCTURE:
1. Hook (1-2 lines): Shocking/controversial statement to stop the scroll
   e.g. "Stop using ChatGPT like this..." / "This AI tool just broke the internet..."
2. Problem/Insight (2-4 lines): Core issue or insight with a real example
3. Solution/Tool (3-5 lines): Present the AI tool or technique — be specific
4. Action Step (1-2 lines): Tell viewer exactly what to try TODAY
5. CTA (1 line): "Follow for daily AI updates!" or "Save this before it disappears!"

Return ONLY the spoken script. No extra formatting."""
    try:
        script = call_ollama(prompt)
        logging.info(f"[Tech] Script generated: {len(script.split())} words")
        return script
    except Exception as e:
        logging.error(f"[Tech] Script failed: {e}")
        return None

def generate_tech_captions(topic, script):
    logging.info(f"[Tech] Generating captions for '{topic}'...")
    prompt = f"""You are a viral AI/tech Instagram manager for @satyamtechinsights.
Generate platform-optimized captions for: "{topic}"
Script snippet: {script[:200]}

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "instagram": "2-3 line caption with emojis and 15 hashtags",
  "tiktok": "short 1-2 line with trending hashtags",
  "linkedin": "professional 3-4 lines with 5 hashtags",
  "facebook": "friendly 2-3 lines with emojis and hashtags",
  "youtube_title": "viral YouTube Shorts title max 60 chars",
  "hook_line": "the single opening hook line only"
}}

Use hashtags from: #AI #ArtificialIntelligence #TechTrends #MachineLearning #AITools #ChatGPT #FutureTech #Coding #TechLife #Innovation #GenAI #Python #AIRevolution #TechInsights #DigitalFuture"""
    try:
        resp = call_ollama(prompt, json_mode=True)
        return json.loads(resp)
    except Exception as e:
        logging.warning(f"[Tech] Caption fallback: {e}")
        return {
            "instagram": f"🤖 {topic}\n\nThis changes everything! 🚀\n\n#AI #ArtificialIntelligence #TechTrends #MachineLearning #AITools #ChatGPT #FutureTech #Coding #TechLife #Innovation #GenAI #Python #AIRevolution #TechInsights #DigitalFuture",
            "tiktok": f"{topic} 🔥 #AI #TechTrends #FutureTech #ChatGPT #AITools",
            "linkedin": f"🚀 {topic}\n\nThe AI revolution is here. Stay ahead of the curve.\n\n#AI #MachineLearning #Innovation #TechTrends #FutureTech",
            "facebook": f"🤖 {topic}!\n\nLike & share to spread the knowledge! 🔥\n\n#AI #TechTrends #ChatGPT",
            "youtube_title": f"{topic[:57]}..." if len(topic) > 57 else topic,
            "hook_line": "Stop everything — this AI just changed the game...",
        }

def brainstorm_tech_topics(done_log):
    logging.info("[Tech] Brainstorming fresh AI/tech topics...")
    done_topics = list(done_log.keys())[:20]
    prompt = f"""You are a viral AI/tech content strategist like @satyamtechinsights (387K Instagram followers).
Brainstorm 20 fresh, viral short-form video topics about:
AI tools, ChatGPT hacks, machine learning, coding with AI, tech breakthroughs, future technology, AI automation.

Requirements:
- Under 12 words each
- Specific, curiosity-driving, action-oriented
- Bold and specific — not generic
- Do NOT repeat: {done_topics}

Return ONLY: {{"topics": ["Topic 1", "Topic 2", ...]}}"""
    try:
        resp   = call_ollama(prompt, json_mode=True)
        parsed = json.loads(resp)
        topics = parsed.get("topics", [])
        logging.info(f"[Tech] Brainstormed {len(topics)} new topics")
        return topics
    except Exception as e:
        logging.error(f"[Tech] Brainstorm failed: {e}")
        return []

# ------------------------------------------------------------------
# Video Pipeline
# ------------------------------------------------------------------

def run_video_pipeline(topic, script):
    logging.info(f"[Tech] Running video pipeline for '{topic}'...")
    cmd = [
        PYTHON_EXE, "cli.py",
        "--video-subject", topic,
        "--video-script",  script,
        "--video-aspect",  "9:16",
        "--stop-at",       "video",
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, env=env,
            encoding="utf-8", errors="replace", cwd=PROJECT_ROOT,
        )
        if proc.returncode != 0:
            logging.error(f"[Tech] cli.py exit {proc.returncode}: {proc.stderr[:500]}")
            return None
        for line in proc.stdout.splitlines():
            if line.strip().startswith('{"task_id":'):
                try:
                    data   = json.loads(line)
                    videos = data.get("result", {}).get("videos", [])
                    if videos:
                        logging.success(f"[Tech] Video ready: {videos[0]}")
                        return videos[0]
                except Exception:
                    pass
    except Exception as e:
        logging.error(f"[Tech] Pipeline exception: {e}")
    return None

# ------------------------------------------------------------------
# Cross-platform Upload
# ------------------------------------------------------------------

def upload_tech_video(topic, video_path, captions, done_log):
    urls_data = {
        "date":       datetime.now().strftime("%Y-%m-%d"),
        "timestamp":  datetime.now().isoformat(),
        "format":     "video",
        "local_path": video_path,
    }

    with upload_lock:
        # Facebook
        try:
            from app.services import meta_upload
            fb_res = meta_upload.upload_to_facebook(
                video_path,
                captions.get("youtube_title", topic),
                captions.get("facebook", f"🤖 {topic} #AI #TechTrends"),
            )
            urls_data["facebook_url"] = fb_res.get("url") if fb_res else "local-only"
            logging.success(f"[Tech] FB: {urls_data['facebook_url']}")
        except Exception as e:
            logging.error(f"[Tech] FB failed: {e}")
            urls_data["facebook_url"] = "local-only"

        # Instagram
        try:
            ig_res = meta_upload.upload_to_instagram(
                video_path, captions.get("instagram", f"🤖 {topic} #AI")
            )
            urls_data["instagram_url"] = ig_res.get("url") if ig_res else "local-only"
            logging.success(f"[Tech] IG: {urls_data['instagram_url']}")
        except Exception as e:
            logging.error(f"[Tech] IG failed: {e}")
            urls_data["instagram_url"] = "local-only"

        # TikTok
        try:
            from app.services.tiktok_upload import upload_to_tiktok
            tk_res = upload_to_tiktok(
                video_path=video_path,
                caption=captions.get("tiktok", f"{topic} #AI"),
            )
            urls_data["tiktok_url"] = tk_res.get("url") if (tk_res and isinstance(tk_res, dict)) else "local-only"
            logging.success(f"[Tech] TikTok: {urls_data['tiktok_url']}")
        except Exception as e:
            logging.error(f"[Tech] TikTok failed: {e}")
            urls_data["tiktok_url"] = "local-only"

        # LinkedIn
        try:
            from app.services.linkedin_playwright import upload_to_linkedin_playwright
            li_res = upload_to_linkedin_playwright(
                video_path, captions.get("linkedin", f"{topic} #AI")
            )
            urls_data["linkedin_url"] = li_res if isinstance(li_res, str) else "local-only"
            logging.success(f"[Tech] LinkedIn: {urls_data['linkedin_url']}")
        except Exception as e:
            logging.error(f"[Tech] LinkedIn failed: {e}")
            urls_data["linkedin_url"] = "local-only"

        with done_log_lock:
            done_log[topic] = urls_data
            save_json(TECH_DONE_PATH, done_log)

        logging.success(f"[Tech] ✅ DONE: '{topic}'")

    return urls_data

# ------------------------------------------------------------------
# Worker
# ------------------------------------------------------------------

def worker(topic, done_log, config):
    logging.info(f"[Tech] ===== PROCESSING: '{topic}' =====")
    script = generate_tech_script(topic)
    if not script:
        return
    captions   = generate_tech_captions(topic, script)
    video_path = run_video_pipeline(topic, script)
    if not video_path or not os.path.exists(video_path):
        logging.error(f"[Tech] No video for '{topic}'. Skipping upload.")
        return
    upload_tech_video(topic, video_path, captions, done_log)

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    logging.info("=" * 60)
    logging.info("  TECH FACTORY — @satyamtechinsights Style")
    logging.info("  Niche: AI Tools | Tech Tutorials | Machine Learning")
    logging.info("=" * 60)

    config   = load_json(TECH_CONFIG_PATH)
    cap      = int(config.get("posts_per_day", 100))
    done_log = load_json(TECH_DONE_PATH)

    topics_data = load_json(TECH_TOPICS_PATH)
    queue       = topics_data.get("queue", [])

    today_str   = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(1 for v in done_log.values() if v.get("date") == today_str)

    logging.info(f"[Tech] Uploaded today: {today_count}/{cap} | Queue: {len(queue)}")

    if today_count >= cap:
        logging.info("[Tech] Daily cap reached. Exiting.")
        return

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}

        while today_count < cap:
            with queue_lock:
                if not queue:
                    new_topics = brainstorm_tech_topics(done_log)
                    if new_topics:
                        queue.extend(new_topics)
                        save_json(TECH_TOPICS_PATH, {"queue": queue})
                    else:
                        logging.warning("[Tech] No new topics. Waiting 30s...")
                        time.sleep(30)
                        continue

                batch = []
                while queue and len(batch) < 2:
                    t = queue.pop(0)
                    if t not in done_log:
                        batch.append(t)
                save_json(TECH_TOPICS_PATH, {"queue": queue})

            if not batch:
                time.sleep(15)
                continue

            import random
            delay = random.randint(10, 30)
            logging.info(f"[Tech] Scheduler delay: {delay}s")
            time.sleep(delay)

            for t in batch:
                future = executor.submit(worker, t, done_log, config)
                futures[future] = t

            for future in as_completed(dict(futures)):
                t = futures.pop(future)
                try:
                    future.result()
                    today_count += 1
                    logging.info(f"[Tech] Progress: {today_count}/{cap}")
                except Exception as e:
                    logging.error(f"[Tech] Worker error for '{t}': {e}")

    logging.info("[Tech] Tech Factory session complete.")

if __name__ == "__main__":
    main()
