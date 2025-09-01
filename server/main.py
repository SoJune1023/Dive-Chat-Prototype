import logging
from flask import Flask

logger = logging.getLogger(__name__)

def create_app():
    try:
        app = Flask(__name__)
    except Exception as e:
        logger.error(f"Failed to create Flask app")
    
    try:
        from .routes.chat_bp import chat_bp
        app.register_blueprint(chat_bp)
    except Exception as e:
        logger.error(f"Failed to register chat_bp")