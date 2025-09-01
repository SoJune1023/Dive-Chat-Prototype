from __future__ import annotations
from typing import Optional
from threading import RLock
from openai import OpenAI
import logging

class GPTManager:
    _client: Optional[OpenAI] = None
    _lock = RLock()

    @classmethod
    def init(cls, api_key: str, timeout: int = 30) -> OpenAI:
        with cls._lock:
            if cls._client is None:
                logging.info("[GPT] initializing client once")
                cls._client = OpenAI(api_key=api_key, timeout=timeout)
            return cls._client

    @classmethod
    def get(cls) -> OpenAI:
        if cls._client is None:
            raise RuntimeError("GPT client not initialized. Call GPTManager.init() on startup.")
        return cls._client

    @classmethod
    def refresh(cls) -> OpenAI:
        """토큰 교체/비상 복구 시 사용."""
        with cls._lock:
            logging.warning("[GPT] refreshing client")
            cls._client = OpenAI()
            return cls._client
