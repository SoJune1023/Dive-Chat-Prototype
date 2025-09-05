# <---------- Caching ---------->
# from ..services.scheduler import cache

# <---------- Logging ---------->
import logging

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.error(f"{msg}{suffix}", exc_info=exc)

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

def get_conn() -> Connection:
    try:
        return engine.connect()
    except Exception as e:
        logger.error("Failed to get DB connection", exc_info=e)
        raise

# <---------- Def exceptions ---------->
class UserNotFound(Exception): ...
class InvalidUserData(Exception): ...
class DatabaseError(Exception): ...
class CacheMissError(Exception): ...

# <---------- Build helpers ---------->
from typing import List, Optional
from pydantic import ValidationError
from schemas import Payload, PrevItem, ImgItem, Response

def load_user_credit(user_id: str) -> int:
    try:
        with get_conn() as conn:
            row = conn.execute(
                text("SELECT credit FROM users WHERE id = :id"),
                {"id": user_id}
            ).mappings().first()

            if row is None:
                raise UserNotFound("User not found")

            credit = row["credit"]

            if credit is None:
                raise InvalidUserData("Invalid user data")

            return int(credit)
    except (UserNotFound, InvalidUserData):
        raise
    except Exception as e:
        raise DatabaseError("Database error") from e

def check_user_credit(user_credit: int, max_credit: int) -> bool:
    return user_credit >= max_credit

def build_img_choices(img_list: Optional[List[ImgItem]]) -> str:
    if not img_list:
        return ""
    return "\n".join(f"{i.key}: {i.url}" for i in img_list)

def build_prompt(public_prompt: str, prompt: str, img_choices: str, note: Optional[str]) -> str:
    parts = [
        (public_prompt or "").strip(),
        (prompt or "").strip(),
    ]
    if note:
        parts.append(note.strip())
    if img_choices:
        parts.extend(["Select one of the following images:", img_choices.strip()])
    return "\n".join(p for p in parts if p)

def build_message(previous: List[PrevItem], message: Optional[str]) -> List[PrevItem]:
    return [m.model_dump() for m in previous] + [{"role": "user", "content": message}]

def is_client_okay(client: any) -> bool:
    return client is not None

# <---------- Def handlers ---------->
from ..services import gpt_5_mini_send_message, gemini_send_message, gpt_setup_client, gemini_setup_client

HANDLERS = {
    "gpt": (gpt_setup_client, gpt_5_mini_send_message),
    "gemini": (gemini_setup_client, gemini_send_message),
}

# <---------- Flows ---------->
from .exceptions import AppError

def payload_system_flow(req: Payload) -> tuple[str, str, Optional[str], Optional[str], int, List[PrevItem],str, str, Optional[List[ImgItem]]]:
    try:
        user = req.user
        character = req.character
        return (
            user.user_id, # str
            user.model, # str
            user.message if user.message else None, # Optional[str]
            user.note if user.note else None, # Optional[str]
            user.max_credit, # int
            user.previous, # List[PrevItem]

            character.prompt, # str
            character.public_prompt, # str
            character.img_list if character.img_list else None # Optional[List[ImgItem]]
        )
    except ValidationError as e:
        raise AppError("Payload system: Wrong payload", 400) from e
    except Exception as e:
        raise Exception("Payload system: Unexpected error", 500) from e

def credit_system_flow(user_id: str, max_credit: int) -> None:
    try:
        user_credit = load_user_credit(user_id)
        if not check_user_credit(user_credit, max_credit):
            raise AppError("Out of credit", 403)
    except UserNotFound as e:
        raise AppError("Credit system: User not found", 404) from e
    except InvalidUserData as e:
        raise AppError("Credit system: Invalid user data", 500) from e
    except DatabaseError as e:
        _log_exc("Database error | Cannot loading user_credit", user_id, e) # DatabaseError는 매우 큰 Error -> log 남김
        raise AppError("Database error", 500) from e

def build_prompt_flow(img_list: Optional[List[ImgItem]], public_prompt: str, prompt: str, note: Optional[str]) -> str:
    try:
        img_choices = build_img_choices(img_list)
        prompt_input = build_prompt(public_prompt, prompt, img_choices, note)
        return prompt_input
    except Exception as e:
        _log_exc("Unexpected error | Could not build prompt_input or img_choices", None, e)
        raise AppError("Cannot build prompt", 500) from e

def build_message_flow(previous: List[PrevItem], message: Optional[str]) -> List[PrevItem]:
    try:
        message_input = build_message(previous, message)
        return message_input
    except Exception as e:
        _log_exc(f"Unexpected error | Could not build message_input", None, e)
        raise AppError("Cannot build message", 500) from e

def send_message_flow(model: str, message_input: List[PrevItem], prompt_input: str) -> Response:
    try:
        if model not in HANDLERS:
            raise AppError("Wrong AI model", 400)

        client_func, send_func = HANDLERS[model]

        client = client_func()

        raw = send_func(client, message_input, prompt_input)
        return raw
    except CacheMissError as e:
        _log_exc("Cache is missing | Client not found", None, e)
        raise AppError(f"{model} client not initialized", 502) from e
    except Exception as e:
        _log_exc("Upstream model error | Cannot get response", None, e)
        raise AppError(f"Could not get response from {model}", 502) from e

# <---------- Handle ---------->
def handle(req: Payload) -> tuple[bool, int, dict]:
    try:
        user_id, model, message, note, max_credit, previous, prompt, public_prompt, img_list = payload_system_flow(req)
        # credit_system_flow(user_id, max_credit)
        prompt_input = build_prompt_flow(img_list, public_prompt, prompt, note)
        message_input = build_message_flow(previous, message)
        response = send_message_flow(model, message_input, prompt_input)
        return True, 200, response.model_dump()
    except AppError as e:
        return False, e.http_status, e.to_dict()
    except Exception as e:
        _log_exc("Unexpected error | Somthing went wrong in handle", getattr(req.user, "user_id", None), e)
        return False, 500, {"error": "Unexpected error in handle"}