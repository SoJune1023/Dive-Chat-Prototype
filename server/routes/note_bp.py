# <---------- Route ---------->
from flask import Blueprint, jsonify, request

from .note_services import handle
from schemas.chat import Payload

note_bp = Blueprint('note_bp', __name__)
@note_bp.route('/onSummary', methods = ['POST'])
def onSend():
    req = Payload(**request.get_json(force=True))
    ok, code, body = handle(req)
    return body, code