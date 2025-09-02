from flask import Flask


def create_app():
    print("line 5")
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        print("line10")
        app = Flask(__name__)
    except Exception as e:
        logger.error(f"Failed to create Flask app")

    try:
        print("line16")
        from .routes.chat_bp import chat_bp
        app.register_blueprint(chat_bp)
        logger.info(f"Success to register chat_bp!")
        print("success..?")
    except Exception as e:
        print(e)
        logger.error(f"Failed to register chat_bp, {e}")
    
    return app