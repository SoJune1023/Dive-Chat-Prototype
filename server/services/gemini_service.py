# <---------- Main ---------->
from google import genai
from google.genai import types
from typing import List

from schemas.ai_response import Response

def gemini_setup_client():
    client = genai.Client(
        api_key="TEMP"
    )
    return client

def gemini_send_message(client: any, message_input: List[dict], prompt_input: str):
    response = client.models.generate_content(
        model="TEMP",
        contents="TEMP",
        config=types.ThinkingConfig("TEMP")
    )