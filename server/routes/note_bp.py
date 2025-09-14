# <---------- Route ---------->
from flask import Blueprint, jsonify, request

from .note_services import summary_handle
from schemas.note import SummaryPayload

note_bp = Blueprint('note_bp', __name__)
@note_bp.route('/onSummary', methods = ['POST'])
def onSend():
    req = SummaryPayload(**request.get_json(force=True))
    ok, code, body = summary_handle(req)
    return body, code