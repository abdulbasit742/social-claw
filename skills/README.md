# Modular Antigravity Skills

This folder contains modular, self-contained scripts designed to be executed via standard python CLI calls.

## 1. Make Video (`make_video.py`)
Generates a complete 9:16 short video from a topic, utilizing Ollama script generation, SAPI voice synthesis, Whisper CPU subtitle extraction, Pexels matching footage download, and FFMPEG compilation.
**Usage**:
```bash
.\venv\Scripts\python.exe skills/make_video.py --topic "Your Topic Here"
```
**Output**: Prints `RESULT_PATH:<path_to_mp4>` on success.

## 2. Publish Video (`publish.py`)
Uploads a compiled mp4 video file to YouTube, Facebook Page, and Instagram Reels (skipping dynamically based on config and credential validation status).
**Usage**:
```bash
.\venv\Scripts\python.exe skills/publish.py --video-path "C:\path\to\video.mp4" --topic "Topic" --script "Script body"
```
**Output**: Prints `RESULT_URLS:{...}` on success.

## 3. Brainstorm Topics (`brainstorm.py`)
Brainstorms fresh engaging topics via local qwen2.5:7b Ollama, avoiding items already present in `done.json`.
**Usage**:
```bash
.\venv\Scripts\python.exe skills/brainstorm.py --niche "Niche name" --count 10
```
**Output**: Prints `RESULT_TOPICS:[...]` on success.

## 4. Daily autonomous run (`daily_run.py`)
Triggers the entire autonomous cycle (brainstorming queue replenishment, video production, multi-platform publishing, and quota cap validation).
**Usage**:
```bash
.\venv\Scripts\python.exe skills/daily_run.py
```

## 5. Pre-flight health check (`health_check.py`)
Runs environmental checks for Ollama tags response, Proxy/Internet connectivity, Credentials freshness, and remaining daily caps.
**Usage**:
```bash
.\venv\Scripts\python.exe skills/health_check.py
```

## 6. AI Clip Generator (`ai_clip.py`)
Generates high-quality B-roll video clips locally using HunyuanVideo-1.5 on RTX 5090.
**Usage**:
```bash
.\venv\Scripts\python.exe skills/ai_clip.py --prompt "Your Prompt Here" --seconds 5.0 --aspect "9:16"
```
**Output**: Prints `RESULT_PATH:<path_to_mp4>` on success.

## 7. Generate Image (`gen_image.py`)
Expands a raw topic into a refined photo-description using local Ollama prompt expansion, then runs FLUX.1 locally on the RTX 5090 to generate a high-quality visual.
**Usage**:
```bash
.\venv\Scripts\python.exe skills/gen_image.py --prompt "Topic or raw description" --aspect "1:1"
```
**Output**: Prints `RESULT_PATH:<path_to_png>` on success.

## 8. Make Social Post (`make_post.py`)
Uses Ollama to generate context-customized captions for LinkedIn, Facebook, and Instagram, then calls `gen_image.py` to generate the accompanying FLUX visual.
**Usage**:
```bash
.\venv\Scripts\python.exe skills/make_post.py --topic "Niche topic"
```
**Output**: Prints `RESULT_JSON:{...}` containing captions and local image path.

