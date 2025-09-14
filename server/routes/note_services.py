# <---------- Logging ---------->
import logging

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.error(f"{msg}{suffix}", exc_info=exc)

# <---------- MySQL ---------->
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, Connection

engine: Engine = create_engine(
    "mysql+pymysql://user:passws@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True
)

def get_conn() -> Connection:
    try:
        return engine.connect()
    except Exception as e:
        logger.error("Failed to get DB connection", exc_info=e)
        raise

# <---------- Payload ---------->
from schemas.note import SummaryPayload, PrevConversation
from schemas.ai_response import SummaryResponse

# <---------- Flows ---------->
from typing import Optional, List

def _summary_payload_system_flow(req: SummaryPayload) -> tuple[str, str, List[str], Optional[str], Optional[List[PrevConversation]]]:
    ...

def _summary_check_cooldown_flow(user_id: str) -> bool:
    ...

def _summary_make_usernote_flow(prevSummaryItem: List[str], prevUserNote: Optional[str], prevConversation: Optional[List[PrevConversation]]) -> SummaryResponse:
    ...

# <---------- Handles ---------->
def summary_handle(req: SummaryPayload) -> tuple[bool, int, dict]: ...