import os
import sys
from loguru import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.services.llm import generate_social_metadata

def test():
    topic = "Scaling Without Sacrifice"
    script = "Learn how to scale your startup without losing your soul."
    logger.info("Starting test...")
    try:
        meta = generate_social_metadata(topic, script, platform="tiktok")
        logger.success(f"Result: {meta}")
    except Exception as e:
        logger.exception(f"Test failed with exception: {e}")

if __name__ == "__main__":
    test()
