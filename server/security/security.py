# <---------- Bycrypt ---------->
from passlib.context import CryptContext

pwd_ctx = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

def hash_password(raw_password: str) -> str:
    return pwd_ctx.hash(raw_password)

def verify_password(hashed: str, password: str) -> bool:
    return pwd_ctx.verify(password, hashed)

def needs_rehash(hashed: str) -> bool:
    return pwd_ctx.needs_update(hashed)