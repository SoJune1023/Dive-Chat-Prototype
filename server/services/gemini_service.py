# gemini_client.py
import os, json, re
from typing import List, Optional, Dict, Any

from google import genai
from google.genai import types
from schemas.ai_response import ChatResponse as ChatRespModel

# ---- Client ----
def gemini_setup_client() -> genai.Client:
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---- Helpers ----
def _mk_text_part(text: str):
    """google.genai 버전차를 흡수하여 안전하게 텍스트 Part 생성"""
    # 신버전 경로
    try:
        return types.Part(text=text)
    except Exception:
        pass
    # 구버전 경로 (키워드 인자!)
    try:
        return types.Part.from_text(text=text)
    except Exception:
        pass
    # 최후 수단: 문자열 그대로 (일부 버전 허용)
    return text

def _to_genai_contents(message_input: List[dict]) -> List[types.Content]:
    contents: List[types.Content] = []
    for m in message_input:
        role = m.get("role", "user")
        content = m.get("content", "")
        part = _mk_text_part(str(content))
        # Content 생성도 버전차 보완
        try:
            contents.append(types.Content(role=role, parts=[part]))
        except Exception:
            # 일부 버전은 parts에 str 허용 X → Part로 강제
            contents.append(types.Content(role=role, parts=[_mk_text_part(str(content))]))
    return contents

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

def _extract_json_text(text: str) -> str:
    """코드블록/잡텍스트에서 첫 JSON 오브젝트만 추출"""
    if not text:
        return ""
    m = _JSON_BLOCK.search(text)
    if m:
        return m.group(1).strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        return text[s:e+1].strip()
    return text.strip()

def _extract_text(resp: Any) -> str:
    """
    google.genai GenerateContentResponse 의 버전별 텍스트 추출 통합:
    - resp.text
    - resp.output_text
    - resp.candidates[0].content.parts[*].text
    """
    # 1) 가장 흔한 속성
    txt = getattr(resp, "text", None) or getattr(resp, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt

    # 2) candidates 트리 순회
    cands = getattr(resp, "candidates", None)
    if cands:
        try:
            parts = getattr(cands[0].content, "parts", []) if cands[0].content else []
            buf = []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    buf.append(t)
            if buf:
                return "\n".join(buf)
        except Exception:
            pass

    # 3) 마지막 시도: 문자열화
    return str(resp)

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
        # 아래 두 항목은 신버전에서 JSON 구조화를 지원.
        # 구버전/호환 이슈가 있으면 try/except로 제거 fallback.
        response_mime_type="application/json",
        response_schema=ChatRespModel.model_json_schema(),
    )
    if seed is not None:
        cfg["seed"] = seed

    try:
        return types.GenerateContentConfig(**cfg)
    except TypeError:
        # 구버전 호환: schema/mime 미지원 시 제거 후 재생성
        cfg.pop("response_mime_type", None)
        cfg.pop("response_schema", None)
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
) -> ChatRespModel:
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

    # --- 스트리밍 ---
    if stream:
        stream_resp = client.models.generate_content(stream=True, **request_kwargs)
        full_text = []
        for chunk in stream_resp:
            # 신버전: chunk.text / 구버전: candidates 파고들기
            t = getattr(chunk, "text", None)
            if isinstance(t, str) and t:
                full_text.append(t)
                continue
            # fallback
            full_text.append(_extract_text(chunk))
        text_joined = "".join(full_text).strip()
        try:
            j = _extract_json_text(text_joined)
            return ChatRespModel.model_validate(json.loads(j))
        except Exception as e:
            raise ValueError(f"Failed to parse stream response into Response: {text_joined}") from e

    # --- 논스트리밍 ---
    resp = client.models.generate_content(**request_kwargs)
    try:
        text = _extract_text(resp)
        j = _extract_json_text(text)
        return ChatRespModel.model_validate(json.loads(j))
    except Exception as e:
        raise ValueError(f"Failed to parse response into Response: {_extract_text(resp)}") from e
