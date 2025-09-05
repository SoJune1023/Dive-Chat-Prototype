# gemini_client.py
import os, json
from typing import List, Optional, Dict, Any, Iterable, Union

from google import genai
from google.genai import types
from schemas.ai_response import Response

from ..config import GEMINI_API_KEY

# ---- Client ----
def gemini_setup_client() -> genai.Client:
    return genai.Client(
        api_key=os.getenv(GEMINI_API_KEY)
    )

# ---- Helpers ----
def _to_genai_contents(message_input: List[dict]) -> List[types.Content]:
    contents: List[types.Content] = []
    for m in message_input:
        role = m.get("role", "user")
        content = m.get("content", "")
        contents.append(types.Content(role=role, parts=[types.Part.from_text(str(content))]))
    return contents

def _build_config(
    *,
    prompt_input: str,
    temperature: float,
    top_p: float,
    max_output_tokens: int,
    seed: Optional[int],
) -> types.GenerateContentConfig:
    cfg: Dict[str, Any] = dict(
        system_instruction=prompt_input,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json",
        response_schema=Response.model_json_schema(),
    )
    if seed is not None:
        cfg["seed"] = seed
    return types.GenerateContentConfig(**cfg)

# ---- Request ----
def gemini_send_message(
    client: genai.Client,
    message_input: List[dict],
    prompt_input: str,
    *,
    model: str = "gemini-2.0-flash",
    temperature: float = 0.7,
    top_p: float = 1.0,
    max_output_tokens: int = 1024,
    seed: Optional[int] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    stream: bool = False,
) -> Response:
    contents = _to_genai_contents(message_input)
    config = _build_config(
        prompt_input=prompt_input,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        seed=seed,
    )

    request_kwargs: Dict[str, Any] = dict(model=model, contents=contents, config=config)
    if extra_headers:
        request_kwargs["extra_headers"] = extra_headers
    if timeout is not None:
        request_kwargs["request_options"] = {"timeout": timeout}

    if stream:
        # 스트리밍 모드: 청크 모아서 최종 텍스트 생성
        stream_resp = client.models.generate_content(stream=True, **request_kwargs)
        full_text = ""
        for chunk in stream_resp:
            if chunk.text:
                full_text += chunk.text
        try:
            return Response.model_validate(json.loads(full_text))
        except Exception:
            raise ValueError(f"Failed to parse stream response into Response: {full_text}")

    # non-stream 모드
    resp = client.models.generate_content(**request_kwargs)
    try:
        return Response.model_validate(json.loads(resp.text))
    except Exception:
        raise ValueError(f"Failed to parse response into Response: {resp.text}")
