import re
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class PersonIn(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name:  str = Field(..., min_length=1, max_length=80)
    age:        int = Field(..., ge=0, le=120)
    height_cm:  Optional[float] = Field(None, ge=0, le=300)
    weight_kg:  Optional[float] = Field(None, ge=0, le=500)
    cep:        Optional[str] = Field(None, min_length=8, max_length=9)
    
    @validator('cep')
    def validate_cep(cls, v):
        if v is None:
            return v
        # Remove todos os caracteres não numéricos
        cep_limpo = re.sub(r"\D", "", v)
        if len(cep_limpo) != 8:
            raise ValueError('CEP deve ter exatamente 8 dígitos')
        return cep_limpo

class PersonOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    age: int
    height_cm: Optional[float]
    weight_kg: Optional[float]
    cep: Optional[str]
    # Campos de endereço vindos do ViaCEP
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    created_at: Optional[datetime] = None

class PersonUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=80)
    last_name:  Optional[str] = Field(None, min_length=1, max_length=80)
    age:        Optional[int] = Field(None, ge=0, le=120)
    height_cm:  Optional[float] = Field(None, ge=0, le=300)
    weight_kg:  Optional[float] = Field(None, ge=0, le=500)
    cep:        Optional[str] = Field(None, min_length=8, max_length=9)
    
    @validator('cep')
    def validate_cep(cls, v):
        if v is None:
            return v
        cep_limpo = re.sub(r"\D", "", v)
        if len(cep_limpo) != 8:
            raise ValueError('CEP deve ter exatamente 8 dígitos')
        return cep_limpo

class AddressInfo(BaseModel):
    cep: str
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

class CEPUpdate(BaseModel):
    cep: str = Field(..., min_length=8, max_length=9)
    
    @validator('cep')
    def validate_cep(cls, v):
        cep_limpo = re.sub(r"\D", "", v)
        if len(cep_limpo) != 8:
            raise ValueError('CEP deve ter exatamente 8 dígitos')
        return cep_limpo