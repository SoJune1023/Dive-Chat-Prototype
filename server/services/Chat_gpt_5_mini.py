# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl

class MessageItem(BaseModel):
    said: str
    context: str

class Response(BaseModel):
    conversation: List[MessageItem]
    image_selected: HttpUrl

# <---------- Main ---------->
from openai import OpenAI
from typing import List

def gpt_5_mini_setup_client() -> OpenAI:
    client = OpenAI(
        api_key="TEMP (TODO: REPLACE KEY FROM AWS)",
        max_retries="TEMP (TODO: REPLACE VALUE FROM CONFIG)",
        # etc. . .
    )

def gpt_5_mini_send_message(client: OpenAI, message_input: List[dict]):
    response = client.response.create(
        model="TEMP (TODO: REPLACE VALUE ROM CONFIG)",
        text_format=Response,
        input=message_input
        # etc . . .
    )