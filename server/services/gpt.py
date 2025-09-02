# <---------- Main ---------->
from openai import OpenAI
from typing import List

from schemas.ai_response import Response

def gpt_setup_client() -> OpenAI:
    return OpenAI(
        api_key="TEMP (TODO: REPLACE KEY FROM AWS)",
        max_retries="TEMP (TODO: REPLACE VALUE FROM CONFIG)",
        # etc. . .
    )

def gpt_5_mini_send_message(client: OpenAI, message_input: List[dict], prompt_input: str):
    response = client.response.create(
        model="TEMP (TODO: REPLACE VALUE ROM CONFIG)",
        text_format=Response,
        input=message_input
        # etc . . .
    )