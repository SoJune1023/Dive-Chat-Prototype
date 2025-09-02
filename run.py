import sys, os
sys.path.append(os.path.dirname(__file__))

import logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("logs/logs.log", encoding="utf-8"),
              logging.StreamHandler()],
    force=True,   # ← 중요! 기존 핸들러 싹 리셋 후 재설정
)

import logging
logger = logging.getLogger(__name__)

from server.main import create_app

app = create_app()

if __name__ == "__main__":
    try:
        app.run(debug = False, port = 5050)
    except Exception as e:
        logger.error(f"Something went wrong\nError code: {e}")