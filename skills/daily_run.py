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

def run_daily_cycle():
    print("Initiating full autonomous daily run...")
    auto_factory.main()
    print("Daily cycle completed successfully.")

if __name__ == "__main__":
    try:
        run_daily_cycle()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
