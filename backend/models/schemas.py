from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []
    page_url: Optional[str] = None


class PartCard(BaseModel):
    ps_number: str
    name: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    part_url: Optional[str] = None
    in_stock: Optional[bool] = None
    oem_part_number: Optional[str] = None


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    parts: Optional[List[PartCard]] = []
    suggested_queries: Optional[List[str]] = []
