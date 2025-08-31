# <---------- Caching ---------->
claude_client = "TEMP"
gpt_client = "TEMP"

# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class PrevItem(BaseModel):
    role: str
    content: str

class User(BaseModel):
    id: str
    model: str
    message: Optional[str] = " "
    note: Optional[str] = " "
    previous: List[PrevItem]

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

def build_img_choices(img_list: List[ImgItem]) -> any:
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
                'previous': List[{'role': 'system', 'content': <content>}, {'role': 'user', 'content': <content>}]
            },
            'character': {
                'prompt': str,
                'public_prompt': str,
                'img_list': List[{'key': str, 'url': HttpUrl}]
            }
        }
        """
        user     = payload.user
        id       = user.id
        model    = user.model
        message  = user.message
        note     = user.note
        previous = user.previous

        character     = payload.character
        prompt        = character.prompt
        public_prompt = character.public_prompt
        img_list      = character.img_list
        # img_default   = character.img_default
    except ValidationError as e:
        return jsonify({"error": f"Wrong payload."}), 400
    except Exception as e:
        _log_exc("Unexpected error.\nCould not get payload.", id, e)
        return jsonify({"error": f"Unexpected error."}), 500
    
    # TODO: user.id 기반 db 뒤진 다음 credit 체크 --> base64 기반 인코딩 된 형태

    try:
        img_choices = "\n".join([f"{i.key}: {i.url}" for i in img_list])
        prompt_input = f"{public_prompt}\n{prompt}\n{note}\nSelect one of the following images:\n{img_choices}"
    except Exception as e:
        logger.error(
            f"Unexpected error.\n"
            f"Could not build prompt_input or img_choices.\n"
            f"UserID: {id}"
            f"ErrorInfo: {e}"
        )
        return jsonify({"error": f"Cannot build prompt."}), 500

    try:
        message_input = previous + [PrevItem(role="user", content=message)]
    except Exception as e:
        logger.error(
            f"Unexpected error.\n"
            f"Could not build message_input.\n"
            f"UserID: {id}"
            f"ErrorInfo: {e}"
        )
        return jsonify({"error": f"Cannot build message."})

    try:
        # if model == 'claude': -> TODO: Claude model 작업하기.
        #     response = services.claude_send_message(claude_client, message_input)
        if model == 'gpt':
            response = services.gpt_5_mini_send_message(gpt_client, message_input)
            response = services.Chat_gpt_5_mini.Response(**response)
        else:
            logger.warning(f"Wrong AI model request | userID: {id}\npayload: {payload}")
            return jsonify({"error": "Wrong AI model."})
        return jsonify({"conversation": response.conversation, "image": response.image_selected})
    except Exception as e:
        return jsonify({"error": f"Could not get response from {model}."})