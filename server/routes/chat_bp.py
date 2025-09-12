# <---------- Route ---------->
from flask import Blueprint, jsonify, request

from .chat_service import handle
from schemas.chat import Payload

chat_bp = Blueprint('chat_bp', __name__)
@chat_bp.route('/onSend', methods = ['POST'])
def onSend():
    req = Payload(**request.get_json(force=True))
    ok, code, body = handle(req)
    return body, code