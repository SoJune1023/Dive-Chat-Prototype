# <---------- Caching ---------->
gpt_client = "TEMP"
gemini_client = "TEMP"

# <---------- MySQL ---------->
import pymysql

conn = pymysql.connect(
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

from .chat_bp import Payload, ImgItem, PrevItem

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.exception(f"{msg}{suffix}", exc_info=exc)

def build_img_choices(img_list: List[ImgItem]) -> str:
    if not img_list:
        return False
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
# <---------- Handle ---------->
from flask import jsonify
from pydantic import ValidationError

import services

def handle(req: Payload):
    try:
        user     = req.user
        user_id  = user.user_id
        model    = user.model
        message  = user.message
        note     = user.note
        previous = user.previous
        max_credit = user.max_credit

        character     = req.character
        prompt        = character.prompt
        public_prompt = character.public_prompt
        img_list      = character.img_list
        # img_default   = character.img_default
    except ValidationError as e:
        return jsonify({"error": "Wrong payload"}), 400
    except Exception as e:
        _log_exc("Unexpected error. | Could not get payload.", user_id, e)
        return jsonify({"error": "Unexpected error"}), 500
    
    # <---------- Credit System ---------->
    try:
        with conn.cursor() as cursor:
            sql = "SELECT credit FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()

            if result['credit'] is None:
                raise Exception
            user_credit = result["credit"]
    except Exception as e:
        _log_exc(f"Wrong user_id request", user_id, e)
        return jsonify({"error": "Wrong user id"}), 400
    finally:
        conn.close()

    try:
        if user_credit < max_credit:
            return jsonify({"error": "Out of credit"})
    except Exception as e:
        _log_exc("Unexpected error | Could not compare user_credit between max_credit", user_id, e)
        return jsonify({"error": "Unexpected error"}), 500

    # <---------- Prompt Build ---------->
    try:
        img_choices = build_img_choices(img_list)
        prompt_input = build_prompt(public_prompt, prompt, img_choices, note)
    except Exception as e:
        _log_exc("Unexpected error | Could not build prompt_input or img_choices", user_id, e)
        return jsonify({"error": "Cannot build prompt"}), 500

    # <---------- Message Build ---------->
    try:
        message_input = previous + [PrevItem(role="user", content=message)]
    except Exception as e:
        _log_exc(f"Unexpected error | Could not build message_input", user_id, e)
        return jsonify({"error": "Cannot build message"})

    # <---------- Send Message ---------->
    try:
        if model == 'gpt':
            response = services.gpt_5_mini_send_message(gpt_client, message_input, prompt_input)
            response = services.gpt.Response(**response)
        if model == 'gemini':
            response = services.gemini_send_message(gemini_client, message_input, prompt_input)
            response = services.Gemini.Response(**response)
        else:
            _log_exc("Wrong AI model request", user_id, ValidationError)
            return jsonify({"error": "Wrong AI model"})
        return jsonify({"conversation": response.conversation, "image": response.image_selected})
    except Exception as e:
        return jsonify({"error": f"Could not get response from {model}"})