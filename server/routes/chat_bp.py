# <---------- Route ---------->
from flask import Blueprint, request

from .chat_service import chat_handle

chat_bp = Blueprint('chat_bp', __name__)
@chat_bp.route('/onSend', methods = ['POST'])
def onSend():
    ok, code, body = chat_handle(request.get_json(force=True))
    return body, code