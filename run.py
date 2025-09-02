import logging
logger = logging.getLogger(__name__)

from server.main import create_app

if __name__ == "__main__":
    try:
        app = create_app()
        app.run(debug = True, port = 5050)
    except Exception as e:
        logger.error(f"Something went wrong\nError code: {e}")