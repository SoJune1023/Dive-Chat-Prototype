# <---------- Route ---------->
from flask import Blueprint, request

from .prompt_services import approveHandle, uploadHandle

prompt_bp = Blueprint('prompt_bp', __name__)

@prompt_bp.route('/promptUpload', methods = ['POST'])
def promptUpload():
    ok, code, body = uploadHandle(request.get_json(force=True))
    return body, code

@prompt_bp.route('/promptApprove/<int:prompt_id>', methods = ['POST'])
def promptApprove(prompt_id: int):
    ok, code, body = approveHandle(request.get_json(force=True))
    return body, code