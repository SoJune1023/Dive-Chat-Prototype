# <---------- Logging ---------->
import logging

logger = logging.getLogger(__name__)

def _log_exc(msg: str, user_id: str | None, exc: Exception) -> None:
    suffix = f" | user_id: {user_id}" if user_id else ""
    logger.error(f"{msg}{suffix}", exc_info=exc)

# <---------- MySQL ---------->
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

engine: Engine = create_engine(
    "mysql+pymysql://user:passws@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True
)

def _get_conn() -> Connection:
    try:
        return engine.connect()
    except Exception as e:
        logger.error("Failed to get DB connection", exc_info=e)
        raise

# <---------- Def exceptions ---------->
from ..config.exceptions import AppError, ClientError

class UserNotFound(Exception): ...
class InvalidUserData(Exception): ...
class DatabaseError(Exception): ...
class CacheMissError(Exception): ...

# <---------- Build helpers ---------->
from typing import List, Optional
from pydantic import ValidationError
from schemas import ChatPayload, PrevItem, ImgItem, ChatResponse, EvaluationChatPayload

def _load_user_credit(user_id: str) -> int:
    """유저의 크레딧값을 불러온다.
    Args:
        user_id (str): 유저 ID
    Returns:
        int: 유저의 크레딧 값
    Raises:
        UserNotFound: 해당 유저 ID가 존재하지 않는 경우
        InvalidUserData: 크레딧 값이 None인 경우
        DatabaseError: 데이터베이스 접근 도중 오류가 발생한 경우
    """
    try:
        with _get_conn() as conn:
            row = conn.execute(
                text("SELECT credit FROM users WHERE id = :id"),
                {"id": user_id}
            ).mappings().first()

            if row is None:
                raise UserNotFound("User not found")

            credit = row["credit"]

            if credit is None:
                raise InvalidUserData("Invalid user data")

            return int(credit)
    except (UserNotFound, InvalidUserData):
        raise
    except Exception as e:
        raise DatabaseError("Database error") from e

def _build_prompt(public_prompt: str, prompt: str, img_choices: str, note: Optional[str]) -> str:
    """프롬프트를 빌드한다.
    Args:
        public_prompt (str): 공용 프롬프트
        prompt (str): 캐릭터 프롬프트
        img_choices (str): 이미지 url과 그에 맞는 설명
        note (str | None): 유저 노트
    Returns:
        str: 빌드 된 프롬프트 결과물
    """
    parts = [
        (public_prompt or "").strip(),
        (prompt or "").strip(),
    ]
    if note:
        parts.append(note.strip())
    if img_choices:
        parts.extend(["Select one of the following images:", img_choices.strip()])
    return "\n".join(p for p in parts if p)

def _load_user_last_evalutaion_req_time(user_id: str) -> int:
    try:
        with _get_conn() as conn:
            row = conn.execute(
                text("SELECT last_evalutaion_req_time FROM users WHERE id = :id"),
                {"id": user_id}
            ).mappings().first()

            if row is None:
                raise UserNotFound("User not found")

            last_evalutaion_req_time = row["last_evalutaion_req_time"]

            if last_evalutaion_req_time is None:
                raise InvalidUserData("Invalid user data")

            return int(last_evalutaion_req_time)
    except (UserNotFound, InvalidUserData):
        raise
    except Exception as e:
        raise DatabaseError("Database error") from e

def _upload_user_last_evaluation_req_time(user_id: str, now: int) -> None:
    try:
        with _get_conn() as conn:
            with conn.begin():
                conn.execute(
                    text("""
                        INSERT INTO user_notes (user_id, note)
                        VALUES (:user_id, :note)
                        ON DUPLICATE KEY UPDATE note = :note
                    """),
                    {"user_id": user_id, "last_evalutaion_req_time": now}
                )
    except Exception as e:
        _log_exc("Failed to upload last_evaluation_req_time", user_id, e)
        raise DatabaseError("Could not upload last_evaluation_req_time") from e

# <---------- Def handlers ---------->
from ..services import gpt_5_mini_send_message, gemini_send_message, gpt_setup_client, gemini_setup_client

AI__FUNC_HANDLERS = {
    "gpt": (gpt_setup_client, gpt_5_mini_send_message),
    "gemini": (gemini_setup_client, gemini_send_message),
}

from ...prompt import PUBLIC_PROMPT_A, PUBLIC_PROMPT_B, PUBLIC_PROMPT_C

PUBLIC_PROMPT_HANDLERS = {
    "PP_A": (PUBLIC_PROMPT_A),
    "PP_B": (PUBLIC_PROMPT_B),
    "PP_C": (PUBLIC_PROMPT_C)
}

# <---------- Flows ---------->
import uuid as py_uuid
from datetime import datetime, timezone

from ..services.uuid import uuid7_builder
from ..config.config import SYSTEM_MIN_CREDIT, SYSTEM_MAX_CREDIT, EVALUATION_COOLDOWN

def _chat_payload_system_flow(req: ChatPayload) -> tuple[str, str, Optional[str], Optional[str], int, List[PrevItem],str, str, Optional[List[ImgItem]], Optional[str], bool]:
    """요청 페이로드에서 필요한 필드를 추출해 튜플로 반환한다.
    Args:
        req (ChatPayload): 요청 페이로드
    Returns:
        tuple: 다음 순서의 값들
            1. user_id (str)
            2. model (str)
            3. message (str)
            4. note (str | None)
            5. max_credit (int | None)
            6. previous (list)
            7. prompt (str | None)
            8. public_prompt (str | None)
            9. img_list (list)
            10. uuid (str | None)
    Raises:
        ClientError: 필수 필드가 비어 있거나 형식이 잘못된 경우
        AppError: 튜플 반환 중 알 수 없는 오류가 발생한 경우
    """
    try:
        user = req.user
        character = req.character
        info = req.chatInfo
        return (
            user.user_id, # str
            user.model, # str
            user.message if user.message else None, # Optional[str]
            user.note if user.note else None, # Optional[str]
            user.max_credit, # int
            user.previous, # List[PrevItem]

            character.prompt, # str
            character.public_prompt, # str
            character.img_list if character.img_list else None, # Optional[List[ImgItem]]

            info.uuid if info.uuid else None
        )
    except ValidationError as e:
        raise ClientError("Payload system error | Wrong payload", 400) from e
    except Exception as e:
        raise AppError("Payload system error | Unexpected error", 500) from e

def _chat_uuid_flow(uuid: Optional[str]) -> str:
    """채팅방의 고유 uuid를 확인하고 uuid 값이 옳지 않거나 존재하지 않는다면 생성한다. 아닐 경우 그대로 반환한다.
    Args:
        uuid (str): 채팅방 고유 uuid
    Returns:
        str: 새로 생성 된 uuid(uuid 값이 옳지 않거나 존재하지 않는다면) 혹은 기존 uuid
    Raises:
        AppError: uuid 확인 도중 알 수 없는 에러가 발생한 경우
    """
    try:
        if not uuid or not uuid.strip():
            return uuid7_builder()
        
        try:
            _ = py_uuid.UUID(uuid)
            return uuid
        except ValueError:
            return uuid7_builder()
    except Exception as e:
        _log_exc("Unexpected error at _chat_uuid_flow", None, e)
        raise AppError("Unexpected error", 500) from e

def _chat_credit_system_flow(user_id: str, max_credit: int) -> None:
    """유저 보유 크레딧을 최대 소비 가능 크레딧과 비교한다.
    Args:
        user_id (str): 유저 ID
        max_credit (int): 최대 소비 가능 크레딧
    Raises:
        ClientError: 크레딧이 부족하거나 크레딧 값을 불러올 수 없는 경우
        AppError: 데이터베이스 오류가 발생한 경우
    """
    try:
        user_credit = _load_user_credit(user_id)

        if not SYSTEM_MIN_CREDIT < max_credit < SYSTEM_MAX_CREDIT:
            logger.warning(f"Wrong max_credit arg from {user_id}! Credit: {max_credit}")
            raise ClientError("Wrong max_credit value", 400)
        
        if user_credit < max_credit(user_credit, max_credit):
            raise ClientError("Out of credit", 403)
    except UserNotFound as e:
        raise ClientError("Credit system error | User not found", 404) from e
    except InvalidUserData as e:
        raise ClientError("Credit system error | Invalid user data", 500) from e
    except DatabaseError as e:
        _log_exc("Database error | Cannot loading user_credit", user_id, e) # DatabaseError는 매우 큰 Error -> log 남김
        raise AppError("Database error", 500) from e

def _chat_build_prompt_flow(img_list: Optional[List[ImgItem]], public_prompt: str, prompt: str, note: Optional[str]) -> str:
    """프롬프트를 빌드하고 반환한다.
    Args:
        img_list (list[ImgItem]): 이미지 url과 그것의 설명
        public_prompt (str): 공용 프롬프트
        prompt (str): 캐릭터 프롬프트
        note (str): 유저 노트
    Returns:
        str: 빌드 된 프롬프트 결과
    Raise:
        AppError: 프롬프트 빌드 중 오류가 발생한 경우
    """
    try:
        if not public_prompt in PUBLIC_PROMPT_HANDLERS:
            raise ClientError("Wrong public prompt", 400)

        public = PUBLIC_PROMPT_HANDLERS[public_prompt]

        img_choices = ""
        if img_list:
            img_choices = "\n".join(f"{i.key}: {i.url}" for i in img_list)

        return _build_prompt(public, prompt, img_choices, note)
    except Exception as e:
        _log_exc("Unexpected error | Could not build prompt_input or img_choices", None, e)
        raise AppError("Cannot build prompt", 500) from e

def _chat_build_message_flow(previous: List[PrevItem], message: Optional[str]) -> List[PrevItem]:
    """메시지를 빌드하고 반환한다.
    Args:
        previous (list[PrevItem]): 과거 대화
        message (str | None): 메시지
    Raises:
        AppError: 메시지 빌드에 실패한 경우
    """
    try:
        return [m.model_dump() for m in previous] + [{"role": "user", "content": message}]
    except Exception as e:
        _log_exc(f"Unexpected error | Could not build message_input", None, e)
        raise AppError("Cannot build message", 500) from e

def _chat_send_message_flow(model: str, message_input: List[PrevItem], prompt_input: str) -> ChatResponse:
    """AI 모델에게 메시지를 보내고 그 결과를 반환한다.
    Args:
        model (str): AI 모델
        message_input (list[PrevItem]): 메시지
        primpt_input (str) : 프롬프트
    Return:
        ChatResponse: AI 모델의 답변
    Raises:
        AppError: 클라이언트 생성 실패 혹은 결과를 받지 못한 경우
    """
    try:
        if model not in AI__FUNC_HANDLERS:
            raise ClientError("Wrong AI model", 400)

        client_func, send_func = AI__FUNC_HANDLERS[model]

        client = client_func()

        return send_func(client, message_input, prompt_input)
    except CacheMissError as e:
        _log_exc("Cache is missing | Client not found", None, e)
        raise AppError(f"{model} client not initialized", 502) from e
    except Exception as e:
        _log_exc("Upstream model error | Cannot get response", None, e)
        raise AppError(f"Could not get response from {model}", 502) from e

def _evaluation_check_cooldown_flow(user_id: str) -> None:
    """채팅 평가 시간을 체크한다.
    Args:
        user_id (str): 유저 ID
    Raises:
        ClientError: 유저가 과도한 요청을 날린 경우 혹은 유저를 확인할 수 없는 경우
        AppError: 데이터베이스 오류가 발생한 경우
    """
    try:
        now = int(datetime.now(timezone.utc).timestamp())
        last_req_time = _load_user_last_evalutaion_req_time(user_id)
        elapsed = now - last_req_time

        if elapsed < EVALUATION_COOLDOWN:
            logger.warning(f"Too many evaluation chat requests from {user_id}! (elapsed={elapsed}s)")
            raise ClientError("Too Many Requests", 429)
    except DatabaseError as e:
        _log_exc("Database error while checking evaluation chat cooldown", user_id, e)
        raise AppError("Failed to check evaluation chat cooldown", 500) from e
    except Exception as e:
        _log_exc("Unexpected error while checking evaluation chat cooldown", user_id, e)
        raise AppError("Failed to check evaluation chat cooldown", 500) from e

def _evaluation_upload_reqTime_flow(user_id: str) -> None:
    """채팅 평가 시각을 업로드 한다.
    Args:
        user_id (str): 유저 ID
    Raises:
        ClientError: 유저를 확인할 수 없는 경우
        AppError: 데이터베이스 오류가 발생한 경우
    """
    try:
        now = int(datetime.now(timezone.utc).timestamp())
        _upload_user_last_evaluation_req_time(user_id, now)
    except UserNotFound as e:
        raise ClientError("Evaluation upload error | User not found", 404) from e
    except InvalidUserData as e:
        raise ClientError("Evaluation upload system error | Invalid user data", 500) from e
    except DatabaseError as e:
        _log_exc("Database error | Cannot upload feedback", user_id, e) # DatabaseError는 매우 큰 Error -> log 남김
        raise AppError("Database error", 500) from e

def _evaltauion_upload_feedback_flow(req: EvaluationChatPayload) -> None:
    # TODO: UPLOAD FEEDBACK AT DATABASE
    pass

# <---------- Handle ---------->
def chat_handle(req: ChatPayload) -> tuple[bool, int, dict]:
    try:
        request = ChatPayload(**req)
        user_id, model, message, note, max_credit, previous, prompt, public_prompt, img_list, uuid = _chat_payload_system_flow(request)
        uuid = _chat_uuid_flow(uuid)
        _chat_credit_system_flow(user_id, max_credit)
        prompt_input = _chat_build_prompt_flow(img_list, public_prompt, prompt, note)
        message_input = _chat_build_message_flow(previous, message)
        response = _chat_send_message_flow(model, message_input, prompt_input)
        return True, 200, response.model_dump()
    except ClientError as e:
        return False, e.http_status, e.to_dict()
    except AppError as e:
        return False, e.http_status, e.to_dict()
    except Exception as e:
        _log_exc("Unexpected error | Somthing went wrong in handle", getattr(req.user, "user_id", None), e)
        return False, 500, {"error": "Unexpected error in handle"}

def evaluation_handle(req: EvaluationChatPayload) -> tuple[bool, int, dict]:
    try:
        request = EvaluationChatPayload(**req)
        _evaluation_check_cooldown_flow(request.user)
        _evaluation_upload_reqTime_flow(request.user)
        _evaltauion_upload_feedback_flow(request)
    except ClientError as e:
        return False, e.http_status, e.to_dict()
    except AppError as e:
        return False, e.http_status, e.to_dict()
    except Exception as e:
        _log_exc("Unexpected error | Somthing went wrong in evaluation handle", getattr(req.user, "user_id", None), e)
        return False, 500, {"error": "Unexpected error in evaluation handle"}