# <---------- def exceptions ---------->
from ..config import AppError

# <---------- uuid ---------->
from uuid_extensions import uuid7str

def uuid7_builder() -> str:
    try:
        return uuid7str()
    except Exception as e:
        raise AppError("Unexpected error while build new uuid7", 500)