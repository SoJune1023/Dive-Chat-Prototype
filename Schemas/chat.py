# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class PrevItem(BaseModel):
    role: str
    content: str

class User(BaseModel):
    user_id: str
    model: str
    message: Optional[str] = " "
    note: Optional[str] = " "
    previous: List[PrevItem]
    max_credit: int

class ImgItem(BaseModel):
    key: str
    url: HttpUrl

class Character(BaseModel):
    prompt: str
    public_prompt: str
    img_default: str
    img_list: List[ImgItem]

class Payload(BaseModel):
    user: User
    character: Character