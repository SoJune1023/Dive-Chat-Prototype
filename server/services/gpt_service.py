import os
import uuid
import instructor
from typing import List, Optional, Dict, Any
from openai import OpenAI
from schemas.ai_response import Response as RespModel  # Pydantic schema

from ..config import OPENAI_API_KEY
from ..config import GPT_MINI_MODEL

# <---------- Client ---------->
def gpt_setup_client() -> instructor:
    return instructor.from_openai(
        client=OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=3,
            timeout=30
        )
    )

# <---------- Request ---------->

def gpt_5_mini_send_message(
    client: instructor.Instructor,
    message_input: List[dict],
    prompt_input: str,
    *,
    model: str = "GPT_MINI_MODEL",
    extra_headers: Optional[Dict[str, str]] = None,
) -> RespModel:
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    if extra_headers:
        headers.update(extra_headers)

    resp: RespModel = client.chat.completions.create(
        model=model,
        response_model=RespModel,
        messages=[
            {"role": "system", "content": prompt_input},
            *message_input,
        ],
        extra_headers=headers,
    )

    return resp