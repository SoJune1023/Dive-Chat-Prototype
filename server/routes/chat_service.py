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
from schemas.chat import Payload, ImgItem, PrevItem

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
            pass

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
import services

def handle(req: Payload) -> tuple[bool, int, dict]:
    try:
        user       = req.user
        user_id    = user.user_id
        model      = user.model
        message    = user.message
        note       = user.note
        previous   = user.previous
        max_credit = user.max_credit

        character     = req.character
        prompt        = character.prompt
        public_prompt = character.public_prompt
        img_list      = character.img_list
    except ValidationError as e:
        return False, 400, jsonify({"error": "Wrong payload"})
    except Exception as e:
        _log_exc("Unexpected error. | Could not get payload.", user_id, e)
        return False, 500, jsonify({"error": "Unexpected error"})
    
    # <---------- Credit System ---------->
    try:
        user_credit = load_user_credit(user_id)
    except UserNotFound as e:
        return False, 404, jsonify({"error": "User not found"})
    except InvalidUserData as e:
        return False, 500, jsonify({"error": "Invalid user data"})
    except DatabaseError as e:
        _log_exc("Database error while loading user_credit", user_id, e)
        return False, 500, jsonify({"error": "Database error"})

    try:
        if not check_user_credit(user_credit, max_credit):
            return False, 403, jsonify({"error": "Out of credit"})
    except Exception as e:
        _log_exc("Unexpected error | Could not compare user_credit and max_credit", user_id, e)
        return False, 500, jsonify({"error": "Unexpected error"})

    # <---------- Prompt Build ---------->
    try:
        img_choices = build_img_choices(img_list)
        prompt_input = build_prompt(public_prompt, prompt, img_choices, note)
    except Exception as e:
        _log_exc("Unexpected error | Could not build prompt_input or img_choices", user_id, e)
        return False, 500, jsonify({"error": "Cannot build prompt"})

    # <---------- Message Build ---------->
    try:
        message_input = build_message(previous, message)
    except Exception as e:
        _log_exc(f"Unexpected error | Could not build message_input", user_id, e)
        return False, 500, jsonify({"error": "Cannot build message"})

    # <---------- Send Message ---------->
    try:
        if model == 'gpt':
            response = services.gpt_5_mini_send_message(gpt_client, message_input, prompt_input)
            response = services.gpt.Response(**response)
        elif model == 'gemini':
            response = services.gemini_send_message(gemini_client, message_input, prompt_input)
            response = services.Gemini.Response(**response)
        else:
            _log_exc("Wrong AI model request", user_id, ValidationError)
            return False, 400, jsonify({"error": "Wrong AI model"})
        return True, 200, jsonify({
            "conversation": response.conversation,
            "image": response.image_selected
        })
    except Exception as e:
        _log_exc("Upstream model error", user_id, e)
        return False, 502, jsonify({"error": f"Could not get response from {model}"})