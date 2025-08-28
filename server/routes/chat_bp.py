# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class PrevItem(BaseModel):
    user: str
    system: str

class User(BaseModel):
    id: str
    message: Optional[str] = " "
    note: Optional[str] = " "
    previous: List[PrevItem]

class ImgItem(BaseModel):
    key: str
    url: HttpUrl

class Character(BaseModel):
    prompt: str
    img_default: str
    img_list: List[ImgItem]

class Payload(BaseModel):
    user: User
    character: Character

# <---------- Route ---------->
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

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
                'message': str,
                'note': str,
                'previous': List[{'user': str, 'system': str}]
            },
            'character': {
                'prompt': str,
                'img_default': HttpUrl,
                'img_list': List[{'key': str, 'url': HttpUrl}]
            }
        }
        """
        user     = payload.user
        user_id  = user.user_id
        message  = user.message
        note     = user.note
        previous = user.previous

        character   = payload.character
        prompt      = character.prompt
        img_default = character.img_default
        img_list    = character.img_list
    except ValidationError as e:
        return jsonify({"error": f"Wrong payload. ErrorCode: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error. ErrorCode: {e}"}), 500
    # TODO: prompt build
    # TODO: user.id 기반 db 뒤진 다음 credit 체크 --> base64 기반 인코딩 된 형태
    # TODO: model에 맞게 message send
    # TODO: response 가공 후 jsonify로 return
    pass