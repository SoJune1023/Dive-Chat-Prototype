import os
import uuid
from typing import List, Optional, Dict, Any
from openai import OpenAI
from schemas.ai_response import Response  # Pydantic schema

from ..config import OPENAI_API_KEY

# ---- Client ----
def gpt_setup_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        max_retries=3,
        timeout=30,
    )

# ---- Request ----
def gpt_5_mini_send_message(
    client: OpenAI,
    message_input: List[dict],
    prompt_input: str,
    *,
    model: str = 'gpt-5-mini-2025-08-07',
    temperature: float = 0.7,
    top_p: float = 1.0,
    max_output_tokens: int = 1024,
    seed: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    stream: bool = False,
    tools: Optional[List[dict]] = None,
    tool_choice: Optional[str] = None,
) -> Response:
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    if extra_headers:
        headers.update(extra_headers)

    resp = client.responses.create(
        model=model,
        input=message_input,
        instructions=prompt_input,
        response_format=Response,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        seed=seed,
        metadata=metadata,
        tools=tools,
        tool_choice=tool_choice,
        stream=stream,
        extra_headers=headers,
        timeout=timeout,
    )
    return resp