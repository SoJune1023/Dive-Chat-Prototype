# <---------- Logging ---------->
import logging

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.error(f"{msg}{suffix}", exc_info=exc)

# <---------- MySQL ---------->
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, Connection

engine: Engine = create_engine(
    "mysql+pymysql://user:passws@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True
)

def get_conn() -> Connection:
    try:
        return engine.connect()
    except Exception as e:
        logger.error("Failed to get DB connection", exc_info=e)
        raise

# <---------- Payloads ---------->
from pydantic import BaseModel

class UserInfo(BaseModel):
    email: str
    phone: str
    password: str

class RegisterPayload(BaseModel):
    user_info: UserInfo

class SigninPayload(BaseModel):
    imail: str
    password: str

# <---------- Helpers ---------->
import re
import unicodedata

def norm_email(email: str) -> str:
    return unicodedata.normalize("NFKC", email).strip().lower()

def norm_phone(phone: str) -> str:
    return re.sub(r"\D+", "", unicodedata.normalize("NFKC", phone))

# <---------- Flows ---------->
from .exceptions import AppError

def register_get_payload_flow(payload: RegisterPayload) -> tuple[str, str, str]:
    user_info = payload.user_info
    return(
        user_info.email,
        user_info.phone,
        user_info.password
    )

def set_user_id_flow(email: str, phone: str) -> str:
    normed = norm_email(email) + norm_phone(phone)
    # TODO: 랜덤 arg 추가 후 encoding
    # TODO: return
    pass

# <---------- Handles ---------->
def registerHandle(req: RegisterPayload):
    try:
        email, phone, password = register_get_payload_flow(req)
    except AppError as e:
        return False, e.http_status, e.to_dict()

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