# <---------- Schemas ----------> 
from pydantic import BaseModel
from typing import Optional, List

class PrevConversation(BaseModel):
    user: Optional[str]
    system: str

class SummaryPayload(BaseModel):
    user_id: str
    user_name: str

    prevSummaryItem: List[str]
    prevUserNote: Optional[str]
    prevConversation: Optional[List[PrevConversation]]