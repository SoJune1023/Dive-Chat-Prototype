# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class PrevItem(BaseModel):
    user: str
    system: str

class User(BaseModel):
    id: str
    message: Optional[str] = " "
    user_note: Optional[str] = " "
    previous: List[PrevItem]

class ImgItem(BaseModel):
    key: str
    url: HttpUrl

class Character(BaseModel):
    prompt: str
    img_default: str
    img_list: List[ImgItem]

class Payload(BaseModel):
    user: User
    character: Character