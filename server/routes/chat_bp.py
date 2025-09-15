# <---------- Route ---------->
from flask import Blueprint, jsonify, request

from .chat_service import chat_handle
from schemas.chat import ChatPayload

chat_bp = Blueprint('chat_bp', __name__)
@chat_bp.route('/onSend', methods = ['POST'])
def onSend():
    req = ChatPayload(**request.get_json(force=True))
    ok, code, body = chat_handle(req)
    return body, code