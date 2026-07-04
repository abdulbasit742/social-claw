import os
import sys
import subprocess
import hashlib
from loguru import logger

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.utils import utils

def ai_clip(prompt: str, seconds: int = 3, aspect: str = "9:16") -> str:
    """
    Generate an AI video clip from a text prompt using HunyuanVideo-1.5.
    
    Parameters:
    - prompt (str): Text prompt describing the video subject.
    - seconds (int): Clip duration in seconds.
    - aspect (str): Aspect ratio (9:16, 16:9, 1:1).
    
    Returns:
    - str: Absolute path to the generated MP4 file, or empty string on failure.
    """
    # Create unique hash for caching
    hash_input = f"{prompt.strip().lower()}_{seconds}_{aspect}"
    clip_hash = hashlib.md5(hash_input.encode("utf-8")).hexdigest()
    
    # Save to storage/cache_videos
    cache_dir = os.path.join(project_root, "storage", "cache_videos")
    os.makedirs(cache_dir, exist_ok=True)
    video_path = os.path.join(cache_dir, f"ai-vid-{clip_hash}.mp4")
    
    # Check if already generated (Cache hit)
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"AI clip cache hit: {video_path}")
        return video_path
        
    logger.info(f"AI clip cache miss. Initiating HunyuanVideo-1.5 generation for: '{prompt}'...")
    
    # Executable paths
    hunyuan_dir = "C:/Users/absh5/HunyuanVideo15"
    python_exe = os.path.join(hunyuan_dir, "venv", "Scripts", "python.exe")
    generator_script = os.path.join(hunyuan_dir, "generate_clip.py")
    
    if not os.path.exists(python_exe) or not os.path.exists(generator_script):
        logger.error("HunyuanVideo-1.5 environment or generation script not found.")
        return ""
        
    # Setup execution environment with eduroam proxy settings
    env = os.environ.copy()
    env["HTTP_PROXY"] = "http://172.30.10.10:3128"
    env["HTTPS_PROXY"] = "http://172.30.10.10:3128"
    env["NO_PROXY"] = "localhost,127.0.0.1"
    env["PYTHONIOENCODING"] = "utf-8"
    
    cmd = [
        python_exe,
        generator_script,
        "--prompt", prompt,
        "--seconds", str(seconds),
        "--aspect", aspect,
        "--save-path", video_path
    ]
    
    try:
        logger.info(f"Running subprocess command: {' '.join(cmd)}")
        # Run subprocess and capture output
        proc = subprocess.run(
            cmd,
            cwd=hunyuan_dir,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if proc.returncode == 0:
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                logger.success(f"Successfully generated and cached AI clip: {video_path}")
                return video_path
            else:
                logger.error(f"Inference returned success, but output file is missing or empty: {video_path}")
        else:
            logger.error(f"HunyuanVideo generation failed with exit code {proc.returncode}")
            if proc.stderr:
                logger.error(f"Subprocess stderr:\n{proc.stderr}")
            if proc.stdout:
                logger.info(f"Subprocess stdout:\n{proc.stdout}")
                
    except Exception as e:
        logger.exception(f"Failed to launch HunyuanVideo subprocess: {e}")
        
    return ""

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HunyuanVideo-1.5 AI Clip Generator Skill")
    parser.add_argument("--prompt", required=True, type=str, help="Text prompt for video generation")
    parser.add_argument("--seconds", default=3, type=int, help="Target duration in seconds")
    parser.add_argument("--aspect", default="9:16", type=str, help="Aspect ratio (9:16, 16:9, 1:1)")
    
    args = parser.parse_args()
    
    res = ai_clip(prompt=args.prompt, seconds=args.seconds, aspect=args.aspect)
    if res:
        print(f"RESULT_PATH:{res}")
        sys.exit(0)
    else:
        print("RESULT_PATH:", file=sys.stderr)
        sys.exit(1)
