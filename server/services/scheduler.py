from apscheduler.schedulers.background import BackgroundScheduler
from .gpt import gpt_setup_client
from .gemini import gemini_setup_client
from flask_caching import Cache

cache = Cache()

def refresh_gpt_client():
    client = gpt_setup_client()
    cache.set("gpt_client", client)

def refresh_gemini_client():
    client = gemini_setup_client()
    cache.set("gemini_client", client)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_gpt_client, "interval", minutes=5)
    scheduler.add_job(refresh_gemini_client, "interval", minutes=5)
    scheduler.start()
    return scheduler