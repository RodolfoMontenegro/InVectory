from pydantic import BaseModel, Field
from typing import List

class UserModel(BaseModel):
    username: str = Field(..., title="Username", min_length=3, max_length=50)
    password: str = Field(..., title="Password", min_length=8)

class InventoryItem(BaseModel):
    numero_parte: str = Field(..., title="Part Number", min_length=1)
    cantidad: int = Field(..., title="Quantity", ge=0)
    descripcion: str = Field(None, title="Description", min_length=1)

class InventoryResponse(BaseModel):
    items: List[InventoryItem]
