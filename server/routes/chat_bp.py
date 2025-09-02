# <---------- Caching ---------->
gpt_client = "TEMP"
gemini_client = "TEMP"

# <---------- Route ---------->
from flask import Blueprint, jsonify, request

import chat_services
from Schemas.chat import Payload

chat_bp = Blueprint('chat_bp', __name__)
@chat_bp.route('/onSend', methods = ['POST'])
def onSend():
    req = Payload(**request.get_json(force=True))
    ok, code, body = chat_services(req)
    return jsonify(body), code