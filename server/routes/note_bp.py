# <---------- Route ---------->
from flask import Blueprint, jsonify, request

from .note_services import summary_handle, upload_handle

note_bp = Blueprint('note_bp', __name__)
@note_bp.route('/onSummary', methods = ['POST'])
def onSend():
    ok, code, body = summary_handle(request.get_json(force=True))
    return body, code

@note_bp.route('/onUpload', methods = ['POST'])
def onUpload():
    ok, code, body = upload_handle(request.get_json(force=True))
    return body, code