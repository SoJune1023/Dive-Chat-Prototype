# <---------- Caching ---------->
claude_client = "TEMP"
gpt_client = "TEMP"
gemini_client = "TEMP"

# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class PrevItem(BaseModel):
    role: str
    content: str

class User(BaseModel):
    user_id: str
    model: str
    message: Optional[str] = " "
    note: Optional[str] = " "
    previous: List[PrevItem]
    max_credit: int

class ImgItem(BaseModel):
    key: str
    url: HttpUrl

class Character(BaseModel):
    prompt: str
    public_prompt: str
    img_default: str
    img_list: List[ImgItem]

class Payload(BaseModel):
    user: User
    character: Character

# <---------- Helpers ---------->
import logging

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.exception(f"{msg}{suffix}", exc_info=exc)

def build_img_choices(img_list: List[ImgItem]) -> str:
    if not img_list:
        return False
    return "\n".join(f"{i.key}: {i.url}" for i in img_list)

def build_prompt(public_prompt: str, prompt: str, img_choices: List[ImgItem] | bool) -> str:
    if img_choices:
        parts = [
            (public_prompt or "").strip(),
            (prompt or "").strip(),
            "Select one of the following images:",
            (img_choices or "").strip(),
        ]
    elif not img_choices:
        parts = [
            (public_prompt or "").strip(),
            (prompt or "").strip()
        ]
    return "\n".join(p for p in parts if p)

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

# <---------- Route ---------->
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

import server.services as services

chat_bp = Blueprint('chat_bp', __name__)
@chat_bp.route('/onSend', methods = ['POST'])
def onSend():
    try:
        data = request.get_json(force=True)
        payload = Payload(**data)
        """ payload : Dict
        {
            'user': {
                'user_id': str,
                'model' : str,
                'message': str,
                'note': str,
                'previous': List[{'role': 'system', 'content': <content>}, {'role': 'user', 'content': <content>}],
                'max_credit' : int
            },
            'character': {
                'prompt': str,
                'public_prompt': str,
                'img_list': List[{'key': str, 'url': HttpUrl}]
            }
        }
        """
        user     = payload.user
        user_id  = user.user_id
        model    = user.model
        message  = user.message
        note     = user.note
        previous = user.previous
        max_credit = user.max_credit

        character     = payload.character
        prompt        = character.prompt
        public_prompt = character.public_prompt
        img_list      = character.img_list
        # img_default   = character.img_default
    except ValidationError as e:
        return jsonify({"error": "Wrong payload."}), 400
    except Exception as e:
        _log_exc("Unexpected error. | Could not get payload.", user_id, e)
        return jsonify({"error": "Unexpected error."}), 500
    
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

    try:
        img_choices = "\n".join([f"{i.key}: {i.url}" for i in img_list])
        prompt_input = f"{public_prompt}\n{prompt}\n{note}\nSelect one of the following images:\n{img_choices}"
    except Exception as e:
        _log_exc("Unexpected error. | Could not build prompt_input or img_choices.", user_id, e)
        return jsonify({"error": "Cannot build prompt."}), 500

    try:
        message_input = previous + [PrevItem(role="user", content=message)]
    except Exception as e:
        _log_exc(f"Unexpected error. | Could not build message_input.", user_id, e)
        return jsonify({"error": "Cannot build message."})

    try:
        # if model == 'claude': -> TODO: Claude model 작업하기.
        #     response = services.claude_send_message(claude_client, message_input, prompt_input)
        if model == 'gpt':
            response = services.gpt_5_mini_send_message(gpt_client, message_input, prompt_input)
            response = services.Chat_gpt_5_mini.Response(**response)
        if model == 'gemini':
            response = services.gemini_send_message(gemini_client, message_input, prompt_input)
            response = services.Gemini.Response(**response)
        else:
            _log_exc("Wrong AI model request", user_id, ValidationError)
            return jsonify({"error": "Wrong AI model."})
        return jsonify({"conversation": response.conversation, "image": response.image_selected})
    except Exception as e:
        return jsonify({"error": f"Could not get response from {model}."})