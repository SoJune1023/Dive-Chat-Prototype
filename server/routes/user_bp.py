# <---------- Payloads ---------->
from schemas import SigninPayload, RegisterPayload

# <---------- Route ---------->
from flask import Blueprint, request
from schemas import SigninPayload, RegisterPayload

from .user_services import registerHandle, signinHandle

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/register', methods = ['POST'])
def register():
    req = RegisterPayload(**request.get_json(force=True))
    ok, code, body = registerHandle(req)
    return body, code

@user_bp.route('/signin', methods = ['POST'])
def signin():
    req = SigninPayload(**request.get_json(force=True))
    ok, code, body = signinHandle(req)
    return body, code