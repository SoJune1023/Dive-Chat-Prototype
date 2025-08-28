import logging
from flask import Flask

def create_app():
    try:
        app = Flask(__name__)
    except Exception as e:
        logging.error(f"Failed to create Flask app. ErrorCode: {e}")
    
    try:
        from .routes.chat_bp import chat_bp
        app.register_blueprint(chat_bp)
    except Exception as e:
        logging.error(f"Failed to register chat_bp. ErrorCode: {e}")