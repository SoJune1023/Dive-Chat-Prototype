# <---------- Schemas ---------->
from pydantic import BaseModel, HttpUrl
from typing import List

class MessageItem(BaseModel):
    said: str
    context: str

class ChatResponse(BaseModel):
    conversation: List[MessageItem]
    image_selected: str
    summary: str

class SummaryResponse(BaseModel):
    result: str