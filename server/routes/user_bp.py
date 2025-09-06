# <---------- Payloads ---------->
from pydantic import BaseModel

class RegisterPayload(BaseModel): ...

class SigninPayload(BaseModel): ...

# <---------- Handles ---------->
def registerHandle(req: RegisterPayload): ...

def signinHandle(req: SigninPayload): ...

# <---------- Route ---------->
from flask import Blueprint, request

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