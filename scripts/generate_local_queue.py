import os
import json
import sys
from datetime import datetime

# project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts import auto_factory
from skills import make_video

def main():
    topics_path = "scripts/topics.json"
    done_path = "scripts/done.json"
    
    # Load queue
    queue_data = auto_factory.load_json(topics_path)
    queue = queue_data.get("queue", [])
    done = auto_factory.load_json(done_path)
    
    to_generate = ["Entrepreneurial Bootcamps", "Mind Over Market", "Sales Hacks Under $10", "Networking Over Coffee"]
    
    # Filter queue to remove these topics
    new_queue = [t for t in queue if t not in to_generate]
    queue_data["queue"] = new_queue
    auto_factory.save_json(topics_path, queue_data)
    
    print(f"Removed {to_generate} from queue. Beginning generation...")
    
    for topic in to_generate:
        try:
            print(f"\n--- Generating Local Video for: {topic} ---")
            video_path = make_video.make_video(topic)
            
            # Find script
            task_folder = os.path.dirname(video_path)
            script_text = ""
            try:
                with open(os.path.join(task_folder, "script.json"), "r", encoding="utf-8") as sf:
                    sdata = json.load(sf)
                    script_text = sdata.get("script", "")
            except Exception:
                pass
                
            done[topic] = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().isoformat(),
                "youtube_url": "local-only",
                "facebook_url": "local-only",
                "instagram_url": "local-only",
                "script": script_text,
                "local_video_path": video_path
            }
            auto_factory.save_json(done_path, done)
            print(f"Logged local-only topic '{topic}' at path: {video_path}")
        except Exception as e:
            print(f"Failed to generate offline video for '{topic}': {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
