# <---------- Route ---------->
from flask import Blueprint, jsonify, request

import server.routes.chat_service as chat_service
from schemas.chat import Payload

chat_bp = Blueprint('chat_bp', __name__)
@chat_bp.route('/onSend', methods = ['POST'])
def onSend():
    req = Payload(**request.get_json(force=True))
    ok, code, body = chat_service.handle(req)
    return jsonify(body), code