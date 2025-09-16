# <---------- Payloads ---------->
from schemas import SigninPayload, RegisterPayload

# <---------- Route ---------->
from flask import Blueprint, request

from .user_services import registerHandle, signinHandle

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/register', methods = ['POST'])
def register():
    ok, code, body = registerHandle(request.get_json(force=True))
    return body, code

@user_bp.route('/signin', methods = ['POST'])
def signin():
    ok, code, body = signinHandle(request.get_json(force=True))
    return body, code