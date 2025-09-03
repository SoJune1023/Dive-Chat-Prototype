# <---------- Caching (TEMP) ---------->
gpt_client = "TEMP"
gemini_client = "TEMP"

# <---------- MySQL (TEMP) ---------->
import pymysql
from pymysql.connections import Connection

def get_conn() -> Connection:
    return pymysql.connect(
        host='localhost',
        user='user',
        password='passws',
        database='db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# <---------- Helpers ---------->
import logging
from typing import List, Optional
from flask import jsonify
from pydantic import ValidationError
from schemas import Payload, PrevItem, ImgItem, Response

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.exception(f"{msg}{suffix}", exc_info=exc)

class UserNotFound(Exception): ...
class InvalidUserData(Exception): ...
class DatabaseError(Exception): ...

def load_user_credit(user_id: str) -> int:
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT credit FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row is None:
                raise UserNotFound("User not found")
            credit = row.get("credit")
            if credit is None:
                raise InvalidUserData("Invalid user data")
            return credit
    except (UserNotFound, InvalidUserData):
        raise
    except Exception as e:
        raise DatabaseError("Database error") from e
    finally:
        try:
            conn.close()
        except Exception:
            _log_exc("Cannot close connection", None, e)

def check_user_credit(user_credit: int, max_credit: int) -> bool:
    return user_credit >= max_credit

def build_img_choices(img_list: List[ImgItem]) -> str:
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

def build_message(previous: List[PrevItem], message: str) -> List[PrevItem]:
    return previous + [PrevItem(role="user", content=message)]
    
# <---------- Handle ---------->
from ..services import gpt_5_mini_send_message, gemini_send_message

def payload_system_flow(req: Payload) -> tuple[str, str, Optional[str], Optional[str], int, List[PrevItem], str, str, Optional[List[ImgItem]]]:
    try:
        user       = req.user
        user_id    = user.user_id # str
        model      = user.model # str
        message    = user.message # Optional[str]
        note       = user.note # Optional[str]
        max_credit = user.max_credit # int
        previous   = user.previous # list[{user: str}, {system: str}, . . .]

        character     = req.character
        prompt        = character.prompt # str
        public_prompt = character.public_prompt # str
        img_list      = character.img_list # Optional[list[{key: str, url: http5}]]
        return tuple[user_id, model, message, note, max_credit, previous, prompt, public_prompt, img_list]
    except ValidationError:
        raise ValidationError("Payload system: Wrong payload", 400)
    except Exception:
        raise Exception("Payload system: Unexpected error", 500)

def credit_system_flow(user_id: str, max_credit: int) -> None:
    try:
        user_credit = load_user_credit(user_id)
        if not check_user_credit(user_credit, max_credit):
            raise Exception("Out of credit", 403)
    except UserNotFound as e:
        raise UserNotFound("Credit system: User not found", 404)
    except InvalidUserData as e:
        raise InvalidUserData("Credit system: Invalid user data", 500)
    except DatabaseError as e:
        _log_exc("Database error while loading user_credit", user_id, e) # DatabaseError는 매우 큰 Erroe -> log 남김
        raise DatabaseError("Database error", 500)

def build_prompt_flow(img_list: List[ImgItem], public_prompt: str, prompt: str, note: str) -> str:
    try:
        img_choices = build_img_choices(img_list)
        prompt_input = build_prompt(public_prompt, prompt, img_choices, note)
        return prompt_input
    except Exception as e:
        _log_exc("Unexpected error | Could not build prompt_input or img_choices", None, e)
        return False, 500, jsonify({"error": "Cannot build prompt"})

def build_message_flow(previous: List[PrevItem], message: str) -> List[PrevItem]:
    try:
        message_input = build_message(previous, message)
        return message_input
    except Exception as e:
        _log_exc(f"Unexpected error | Could not build message_input", None, e)
        raise Exception("Cannot build message", 500)

def send_message_flow(model: str, message_input: List[PrevItem], prompt_input: str) -> Response:
    try:
        if model == 'gpt':
            response = gpt_5_mini_send_message(gpt_client, message_input, prompt_input)
            response = Response(**response)
        elif model == 'gemini':
            response = gemini_send_message(gemini_client, message_input, prompt_input)
            response = Response(**response)
        else:
            raise ValidationError("Wrong AI model", 400)
        return response
    except Exception as e:
        _log_exc("Upstream model error", None, e)
        raise (f"Could not get response from {model}", 502)

def handle(req: Payload) -> tuple[bool, int, dict]:
    try:
        user_id, model, message, note, max_credit, previous, prompt, public_prompt, img_list = payload_system_flow(req)
        credit_system_flow(user_id, max_credit)
        prompt_input = build_prompt_flow(img_list, public_prompt, prompt, note)
        message_input = build_message_flow(previous, message)
        response = send_message_flow(model, message_input, prompt_input)
        return True, 200, response
    # TODO: custom error 계층 박어넣기
    except Exception as e:
        _log_exc("Error in handle", getattr(req.user, "user_id", None), e)
        return False, 500, jsonify({"error": "Unexcept error in gandle"})