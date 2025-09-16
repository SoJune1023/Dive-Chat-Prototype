# <---------- Logging ---------->
import logging

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.error(f"{msg}{suffix}", exc_info=exc)

# <---------- Def exceptions ---------->
from config import AppError, ClientError
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
from schemas import SummaryPayload, PrevConversation, UploadPayload, SummaryResponse

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
    
def _format_summary_input(prevSummaryItem: List[str], prevUserNote: Optional[str], prevConversation: Optional[List[PrevConversation]], user_name: str) -> str:
    try:
        parts = []

        parts.append(f"User name: {user_name}")

        parts.append(f"Conversation Summary: {', '.join(prevSummaryItem)}")

        if prevUserNote:
            parts.append(f"Previous UserNote: {prevUserNote}")

        if prevConversation:
            joined_convs = " | ".join(
                f"user: {conv.user or 'None'}, system: {conv.system}"
                for conv in prevConversation
            )
            parts.append("Conversation: " + joined_convs)

        return " || ".join(parts)
    except Exception:
        raise

def _upload_userNote_new(user_id: str, new_note: str) -> None:
    try:
        with _get_conn() as conn:
            with conn.begin():
                conn.execute(
                    text("""
                        INSERT INTO user_notes (user_id, note)
                        VALUES (:user_id, :note)
                        ON DUPLICATE KEY UPDATE note = :note
                    """),
                    {"user_id": user_id, "note": new_note}
                )
    except Exception as e:
        _log_exc("Failed to upload user note", user_id, e)
        raise DatabaseError("Could not upload user note") from e

def _load_user_last_upload_req_time(user_id: str) -> int:
    try:
        with _get_conn() as conn:
            row = conn.execute(
                text("SELECT last_upload_req_time FROM users WHERE id = :id"),
                {"id": user_id}
            ).mappings().first()

            if row is None:
                raise UserNotFound("User not found")

            last_upload_req_time = row["last_upload_req_time"]

            if last_upload_req_time is None:
                raise InvalidUserData("Invalid user data")

            return int(last_upload_req_time)
    except (UserNotFound, InvalidUserData):
        raise
    except Exception as e:
        raise DatabaseError("Database error") from e

# <---------- Flows ---------->
from typing import Optional, List
from datetime import datetime, timezone

from ..config import SUMMARY_COOLDOWN, SUMMARY_MAX_PREV, SUMMARY_PROMPT, UPLOAD_COOLDOWN

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
        now = int(datetime.now(timezone.utc).timestamp())
        last_req_time = _load_user_last_summary_req_time(user_id)
        elapsed = now - last_req_time

        if elapsed < SUMMARY_COOLDOWN:
            logger.warning(f"Too many upload requests from {user_id}! (elapsed={elapsed}s)")
            raise ClientError("Too Many Requests", 429)
    except DatabaseError as e:
        _log_exc("Database error while check user note cool down", None, e)
        raise AppError("Database error while check user note cool down", 500) from e
    except Exception as e:
        _log_exc("Unexpected error while check user note cool down", None, e)
        raise AppError("Unexpected error while check user note cool down", 500) from e

def _summary_format_summary_input_flow(
    prevSummaryItem: List[str],
    prevUserNote: Optional[str],
    prevConversation: Optional[List[PrevConversation]],
    user_name: str
) -> str:
    try:
        if prevConversation and len(prevConversation) > SUMMARY_MAX_PREV:
            raise ClientError("Bad request", 400)
        
        return _format_summary_input(prevSummaryItem, prevUserNote, prevConversation, user_name)
    except Exception as e:
        raise AppError("Unexpected error while build user note input", 500) from e

def _summary_send_to_gpt_flow(format_summary_input: str) -> SummaryResponse:
    try:
        client = gpt_setup_client()

        return gpt_5_mini_summary_note(client, format_summary_input, SUMMARY_PROMPT)
    except Exception as e:
        raise AppError("Unexpected error while user note request to gpt") from e
    
def _upload_payload_system_flow(req: UploadPayload) -> tuple[str, str]:
    try:
        return(
            req.user_id,
            req.new_note
        )
    except ValueError as e:
        raise ClientError("Payload system error | Wrong payload", 400) from e
    except Exception as e:
        raise Exception("Payload system error | Unexpected error", 500) from e

def _upload_check_cooldown_flow(user_id: str) -> None:
    try:
        now = int(datetime.now(timezone.utc).timestamp())
        last_req_time = _load_user_last_upload_req_time(user_id)
        elapsed = now - last_req_time

        if elapsed < UPLOAD_COOLDOWN:
            logger.warning(f"Too many upload requests from {user_id}! (elapsed={elapsed}s)")
            raise ClientError("Too Many Requests", 429)
    except DatabaseError as e:
        _log_exc("Database error while checking upload cooldown", user_id, e)
        raise AppError("Failed to check upload cooldown", 500) from e
    except Exception as e:
        _log_exc("Unexpected error while checking upload cooldown", user_id, e)
        raise AppError("Failed to check upload cooldown", 500) from e
    
def _upload_userNote_new_flow(user_id: str, new_note: str) -> None:
    try:
        _upload_userNote_new(user_id, new_note)
    except DatabaseError as e:
        _log_exc("Database error while upload user note cool down", None, e)
        raise AppError("Database error while upload user note cool down", 500) from e
    except Exception as e:
        _log_exc("Unexpected error while upload user note cool down", None, e)
        raise AppError("Unexpected error while upload user note cool down", 500) from e

# <---------- Handles ---------->
def summary_handle(req: SummaryPayload) -> tuple[bool, int, dict]:
    try:
        user_id, user_name, prevSummaryItem, prevUserNote, prevConversation = _summary_payload_system_flow(req)
        _summary_check_cooldown_flow(user_id)
        format_summary_input = _summary_format_summary_input_flow(prevSummaryItem, prevUserNote, prevConversation, user_name)
        response = _summary_send_to_gpt_flow(format_summary_input)
        return True, 200, response
    except ClientError as e:
        return False, e.http_status, e.to_dict()
    except AppError as e:
        return False, e.http_status, e.to_dict()
    except Exception as e:
        _log_exc("Unexpected error while build user note", None, e)
        return False, 500, {"error": "something went wrong while build user note"}
    
def upload_handle(req: UploadPayload) -> tuple[bool, int, dict | None]:
    try:
        user_id, new_note = _upload_payload_system_flow(req)
        _upload_check_cooldown_flow(user_id)
        _upload_userNote_new_flow(user_id, new_note)
    except ClientError as e:
        return False, e.http_status, e.to_dict()
    except AppError as e:
        return False, e.http_status, e.to_dict()
    except Exception as e:
        _log_exc("Unexpected error while build user note", None, e)
        return False, 500, {"error": "something went wrong while upload user note"}