import sys
import os

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts import pre_flight_check

if __name__ == "__main__":
    try:
        pre_flight_check.main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
