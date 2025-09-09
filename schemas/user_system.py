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