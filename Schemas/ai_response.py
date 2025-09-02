# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl
from typing import List

class MessageItem(BaseModel):
    said: str
    context: str

class Response(BaseModel):
    conversation: List[MessageItem]
    image_selected: HttpUrl