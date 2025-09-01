from __future__ import annotations
from threading import RLock
from typing import Optional
import logging
from openai import OpenAI

from .gpt import gpt_setup_client

class GPTManager:
    _client: Optional[OpenAI] = None
    _lock = RLock()

    @classmethod
    def init(cls) -> OpenAI:
        with cls._lock:
            if cls._client is None:
                logging.info("[GPT] Initializing client once")
                cls._client = gpt_setup_client()
            return cls._client

    @classmethod
    def get(cls) -> OpenAI:
        if cls._client is None:
            raise RuntimeError("GPT client not initialized. Call GPTManager.init() first.")
        return cls._client

    @classmethod
    def refresh(cls) -> OpenAI:
        with cls._lock:
            logging.warning("[GPT] Refreshing client")
            cls._client = gpt_setup_client()
            return cls._client
