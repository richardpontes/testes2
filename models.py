from pydantic import BaseModel, Field
from typing import Optional

class PersonIn(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name:  str = Field(..., min_length=1, max_length=80)
    age:        int = Field(..., ge=0, le=120)
    height_cm:  Optional[float] = Field(None, ge=0)
    weight_kg:  Optional[float] = Field(None, ge=0)
    cep:        Optional[str]   = Field(None, min_length=8, max_length=9)

class PersonOut(PersonIn):
    id: int