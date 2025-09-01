# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl

class MessageItem(BaseModel):
    said: str
    context: str

class Response(BaseModel):
    conversation: List[MessageItem]
    image_selected: HttpUrl

# <---------- Main ---------->
from google import genai
from google.genai import types
from typing import List

def gemini_setup_client():
    client = genai.Client(
        api_key="TEMP"
    )
    return client

def gemini_send_message(client: any, message_input: List[dict]):
    response = client.models.generate_content(
        model="TEMP",
        contents="TEMP",
        config=types.ThinkingConfig("TEMP")
    )