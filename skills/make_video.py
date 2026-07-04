import sys
import os
import argparse
import subprocess
import json

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts import auto_factory

def make_video(topic: str) -> str:
    print(f"Generating video for topic: '{topic}'...")
    
    # 1. Generate Script
    config = auto_factory.load_config()
    niche = config.get("niche", "entrepreneurship")
    script = auto_factory.generate_script(topic, niche)
    if not script:
        raise Exception(f"Failed to generate script for topic: '{topic}'")
        
    print("Script generated successfully.")
    
    # 2. Run cli.py
    cmd = [
        sys.executable,
        "cli.py",
        "--video-subject", topic,
        "--video-script", script,
        "--video-aspect", "9:16",
        "--stop-at", "video"
    ]
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8")
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise Exception("cli.py failed to execute pipeline.")
        
    # Parse video path
    video_path = None
    for line in proc.stdout.splitlines():
        if line.strip().startswith('{"task_id":'):
            try:
                data = json.loads(line)
                video_path = data.get("result", {}).get("videos", [None])[0]
                break
            except Exception:
                pass
                
    if not video_path or not os.path.exists(video_path):
        raise Exception("Failed to locate compiled video in output.")
        
    print(f"Video generated successfully at: {video_path}")
    return video_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="Topic for the video")
    args = parser.parse_args()
    try:
        path = make_video(args.topic)
        print(f"RESULT_PATH:{path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
