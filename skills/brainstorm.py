import sys
import os
import argparse
import json

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts import auto_factory

def brainstorm_topics(niche: str, count: int) -> list:
    done_log = auto_factory.load_json(auto_factory.DONE_PATH)
    topics = auto_factory.brainstorm_topics(niche, done_log)
    if topics:
        # Cap to requested count
        topics = topics[:count]
    return topics or []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", required=True, help="Niche area to brainstorm")
    parser.add_argument("--count", type=int, default=10, help="Number of topics to brainstorm")
    args = parser.parse_args()
    
    try:
        topics = brainstorm_topics(args.niche, args.count)
        print(f"RESULT_TOPICS:{json.dumps(topics)}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
