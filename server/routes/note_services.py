# <---------- Logging ---------->
import logging

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.error(f"{msg}{suffix}", exc_info=exc)

# <---------- Def exceptions ---------->
from .exceptions import AppError
from .exceptions import ClientError
from pydantic import ValidationError

class UserNotFound(Exception): ...
class InvalidUserData(Exception): ...
class DatabaseError(Exception): ...
class CacheMissError(Exception): ...

# <---------- MySQL ---------->
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

engine: Engine = create_engine(
    "mysql+pymysql://user:passws@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True
)

def _get_conn() -> Connection:
    try:
        return engine.connect()
    except Exception as e:
        logger.error("Failed to get DB connection", exc_info=e)
        raise

# <---------- Payload ---------->
from schemas.note import SummaryPayload, PrevConversation
from schemas.ai_response import SummaryResponse

# <---------- Helpers ---------->
def _load_user_last_summary_req_time(user_id: str) -> int:
    try:
        with _get_conn() as conn:
            row = conn.execute(
                text("SELECT last_summary_req_time FROM users WHERE id = :id"),
                {"id": user_id}
            ).mappings().first()

            if row is None:
                raise UserNotFound("User not found")

            last_summary_req_time = row["last_summary_req_time"]

            if last_summary_req_time is None:
                raise InvalidUserData("Invalid user data")

            return int(last_summary_req_time)
    except (UserNotFound, InvalidUserData):
        raise
    except Exception as e:
        raise DatabaseError("Database error") from e
    
def _format_summary_input(prevSummaryItem, prevUserNote, prevConversation) -> str:
    parts = []

    if prevSummaryItem:
        parts.append("Conversation Summary: " + ", ".join(prevSummaryItem))

    if prevUserNote:
        parts.append("Previous UserNote: " + prevUserNote)

    if prevConversation:
        joined_convs = " | ".join(
            f"user: {conv.user or 'None'}, system: {conv.system}"
            for conv in prevConversation
        )
        parts.append("Conversation: " + joined_convs)

    return " || ".join(parts)

# <---------- Flows ---------->
from typing import Optional, List
from ..config import SUMMARY_COOLDOWN, SUMMARY_MAX_PREV, SUMMARY_PROMPT

from ..services.gpt_service import gpt_setup_client, gpt_5_mini_summary_note

def _summary_payload_system_flow(req: SummaryPayload) -> tuple[str, str, List[str], Optional[str], Optional[List[PrevConversation]]]:
    try:
        return (
            req.user_id,
            req.user_name,

            req.prevSummaryItem,
            req.prevUserNote if req.prevUserNote else None,
            req.prevConversation if req.prevConversation else None
        )
    except ValidationError as e:
        raise ClientError("Payload system error | Wrong payload", 400) from e
    except Exception as e:
        raise Exception("Payload system error | Unexpected error", 500) from e

def _summary_check_cooldown_flow(user_id: str) -> None:
    try:
        last_summary_req_time = _load_user_last_summary_req_time(user_id)
        if "TEMP TODO: 현재시각 load 후 연산" < SUMMARY_COOLDOWN:
            raise ClientError("Too Many Requests", 429)
    except Exception as e:
        raise AppError("Unexpected error while check user note cool down", 500) from e

def _summary_make_usernote_flow(prevSummaryItem: List[str], prevUserNote: Optional[str], prevConversation: Optional[List[PrevConversation]]) -> str:
    try:
        if len(prevConversation) > SUMMARY_MAX_PREV:
            raise ClientError("Bad request", 400)
        
        return _format_summary_input(prevSummaryItem, prevUserNote, prevConversation)
    except Exception as e:
        raise AppError("Unexpected error while make user note input", 500) from e

def _summary_send_to_gpt_flow(user_note_input: str) -> SummaryResponse:
    try:
        client = gpt_setup_client()

        return gpt_5_mini_summary_note(client, user_note_input, SUMMARY_PROMPT)
    except Exception as e:
        raise AppError("Unexpected error while user note request to gpt") from e

# <---------- Handles ---------->
def summary_handle(req: SummaryPayload) -> tuple[bool, int, dict]: ...