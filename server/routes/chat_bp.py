# <---------- Caching ---------->
client = "TEMP"

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
def prompt_builder(public_prompt: str, prompt: str, img_list: List[ImgItem]) -> str:
    return (f"{public_prompt}\n{prompt}\nSelect one of the following images:\n{[f'{i.key}: {i.url}\n' for i in img_list]}")

# <---------- Route ---------->
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

import server.services as services

chat_bp = Blueprint('chat_bp', __name__)
@chat_bp.route('/onSend', methods = ['POST'])
def onSend():
    # TODO: payload get -> 검증
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
                'img_default': HttpUrl,
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

        character     = payload.character
        prompt        = character.prompt
        public_prompt = character.public_prompt
        img_default   = character.img_default
        img_list      = character.img_list
    except ValidationError as e:
        return jsonify({"error": f"Wrong payload. ErrorCode: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error. ErrorCode: {e}"}), 500
    
    # TODO: user.id 기반 db 뒤진 다음 credit 체크 --> base64 기반 인코딩 된 형태

    try:
        prompt_input = prompt_builder(public_prompt, prompt, img_list)
    except Exception as e:
        return jsonify({"error": f"Cannot build prompt. ErrorCode: {e}"}), 500

    try:
        message_input = previous + [PrevItem(role="user", content=message)]
    except Exception as e:
        return jsonify({"error": f"Cannot build message. ErrorCode: {e}"})

    try:
        if model == 'claude':
            response = services.claude_send_message(client, message_input)
    except Exception as e:
        return jsonify({"error": f"Could not get response from {model}. ErrorCode: {e}"})
    # TODO: response 가공 후 jsonify로 return