from flask import Flask

def create_app():
    import logging
    logger = logging.getLogger(__name__)

    try:
        app = Flask(__name__)
    except Exception as e:
        logger.error(f"Failed to create Flask app")

    # try:
    #     from .services.scheduler import cache, start_scheduler

    #     app.config.update(
    #         CACHE_TYPE="SimpleCache",
    #         CACHE_DEFAULT_TIMEOUT=300
    #     )
    #     cache.init_app(app)
    #     with app.app_context():
    #         from .services.scheduler import refresh_gpt_client, refresh_gemini_client
    #         refresh_gpt_client()
    #         refresh_gemini_client()
    #     start_scheduler()
    # except Exception as e:
    #     logger.error(f"Failed to caching client, {e}")

    try:
        from .routes.chat_bp import chat_bp
        app.register_blueprint(chat_bp)
        logger.info(f"Success to register chat_bp!")
    except Exception as e:
        logger.error(f"Failed to register chat_bp, {e}")
    
    return app