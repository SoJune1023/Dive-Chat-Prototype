# app/services/gpt_manager.py
from __future__ import annotations
from threading import RLock
from typing import Optional
import logging

from .gpt import init_gpt_client  # ← 여기서 팩토리만 가져다 씀

class GPTManager:
    _client = None  # type: Optional[object]
    _lock = RLock()
    _api_key: Optional[str] = None
    _timeout: int = 30

    @classmethod
    def init(cls, api_key: str, timeout: int = 30):
        """최초 1회 초기화. 이미 있으면 그대로 반환."""
        with cls._lock:
            if cls._client is None:
                logging.info("[GPT] initializing client once via factory")
                cls._api_key, cls._timeout = api_key, timeout
                cls._client = init_gpt_client(api_key=api_key, timeout=timeout)
            return cls._client

    @classmethod
    def get(cls):
        if cls._client is None:
            raise RuntimeError("GPT client not initialized. Call GPTManager.init() first.")
        return cls._client

    @classmethod
    def refresh(cls, api_key: str | None = None, timeout: int | None = None):
        """키 교체/회복용. 내부에 저장된 기본값을 쓰되, 인자로 오면 덮어쓴다."""
        with cls._lock:
            if api_key is not None:
                cls._api_key = api_key
            if timeout is not None:
                cls._timeout = timeout
            if cls._api_key is None:
                raise RuntimeError("Cannot refresh without an API key.")
            logging.warning("[GPT] refreshing client via factory")
            cls._client = init_gpt_client(api_key=cls._api_key, timeout=cls._timeout)
            return cls._client
