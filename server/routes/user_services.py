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
from schemas import SigninPayload, RegisterPayload

# <---------- Password policy ---------->
import re

PASSWORD_RE = re.compile(
    r"^(?=.*\d)(?=.*[A-Z])(?=.*[a-z])(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$"
)

# <---------- Helpers ---------->
import phonenumbers
from phonenumbers import PhoneNumberFormat
from email_validator import validate_email

from ..security import hash_password

from .exceptions import AppError, ClientError

def _norm_email(raw_email: str) -> str:
    raw = raw_email.strip().lower()
    email = validate_email(raw, check_deliverability=False)
    return email.email

def _norm_phone(raw_phone: str, default_region: str = "KR") -> str:
    raw = raw_phone.strip()
    num = phonenumbers.parse(raw, None if raw.startswith("+") else default_region)

    if not phonenumbers.is_possible_number(num) or not phonenumbers.is_valid_number(num):
        raise ClientError("Invalid phone number format", 400)

    return phonenumbers.format_number(num, PhoneNumberFormat.E164)

def _validate_and_hash_password(raw_password: str) -> str:
    try:
        if not PASSWORD_RE.fullmatch(raw_password):
            raise ClientError
        return hash_password(raw_password)
    except (TypeError, ValueError, ClientError):
        raise ClientError(f"Invalid password format", 400)
    except Exception:
        raise ClientError("Invalid password format", 400)

# <---------- Flows ---------->
def _register_get_payload_flow(payload: RegisterPayload) -> tuple[str, str, str]:
    user_info = payload.user_info
    return(
        user_info.email,
        user_info.phone,
        user_info.password
    )

def _register_payload_norm_flow(raw_email: str, raw_phone: str, raw_password: str) -> tuple[str, str, str]:
    try:
        return(
        _norm_email(raw_email),
        _norm_phone(raw_phone),
        _validate_and_hash_password(raw_password)
        )
    except ClientError:
        raise
    except Exception as e:
        _log_exc("Payload validate | Something went wrong")
        raise Exception("Payload validate | Something went wrong") from e

# <---------- Handles ---------->
def registerHandle(req: RegisterPayload) -> tuple[bool, int, dict]:
    try:
        raw_email, raw_phone, raw_password = _register_get_payload_flow(req)
        email, phone, password = _register_payload_norm_flow(raw_email, raw_phone, raw_password)
    except ClientError as e:
        return False, e.http_status, e.to_dict()
    except AppError as e:
        return False, e.http_status, e.to_dict()
    except Exception as e:
        return False, 500, {"error": "Something went wrong while register"}

def signinHandle(req: SigninPayload) -> tuple[bool, int, dict]: ...
