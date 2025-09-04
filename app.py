import re
import requests
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
import logging

from models import PersonIn, PersonOut, PersonUpdate, AddressInfo, CEPUpdate
from db import (
    init_pool, close_pool, create_person_db, get_person_db, 
    update_person_db, delete_person_db, list_persons_db
)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Pessoas - FastAPI + Supabase + ViaCEP",
    description="API para gerenciar pessoas com integração automática de endereços via CEP",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_pool()
    logger.info("✅ API iniciada com sucesso!")

@app.on_event("shutdown")
def shutdown():
    close_pool()
    logger.info("✅ API encerrada")

@app.get("/health")
def health():
    """Endpoint de saúde da API"""
    return {
        "status": "ok", 
        "message": "API funcionando!", 
        "version": "2.0.0"
    }

# ---------- Helper ViaCEP com Cache ----------
@lru_cache(maxsize=1000)
def fetch_via_cep_cached(cep: str) -> Optional[Dict[str, Any]]:
    """Busca endereço no ViaCEP com cache"""
    try:
        cep_limpo = re.sub(r"\D", "", cep)
        if len(cep_limpo) != 8:
            return None
            
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("erro"):
                return {
                    "cep": data.get("cep", "").replace("-", ""),
                    "street": data.get("logradouro") or None,
                    "neighborhood": data.get("bairro") or None,
                    "city": data.get("localidade") or None,
                    "state": data.get("uf") or None
                }
        return None
    except requests.RequestException as e:
        logger.warning(f"Erro ao consultar ViaCEP para CEP {cep}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao consultar ViaCEP: {e}")
        return None

def fetch_via_cep(cep: str) -> Optional[Dict[str, Any]]:
    """Wrapper sem cache para casos específicos"""
    return fetch_via_cep_cached(cep)

# ---------- ROTAS CRUD COMPLETAS ----------

@app.post("/persons", response_model=PersonOut, status_code=201)
def create_person(person: PersonIn):
    """Criar uma nova pessoa"""
    try:
        # Busca endereço pelo CEP se fornecido
        endereco = None
        if person.cep:
            endereco = fetch_via_cep(person.cep)
            if not endereco:
                raise HTTPException(
                    status_code=400, 
                    detail=f"CEP {person.cep} não encontrado ou inválido"
                )
        
        # Prepara dados para inserção
        person_data = {
            'first_name': person.first_name,
            'last_name': person.last_name,
            'age': person.age,
            'height_cm': person.height_cm,
            'weight_kg': person.weight_kg,
            'cep': endereco.get("cep") if endereco else person.cep,
            'street': endereco.get("street") if endereco else None,
            'neighborhood': endereco.get("neighborhood") if endereco else None,
            'city': endereco.get("city") if endereco else None,
            'state': endereco.get("state") if endereco else None
        }
        
        # Cria a pessoa no banco
        resultado = create_person_db(person_data)
        
        if not resultado:
            raise HTTPException(500, detail="Erro ao criar pessoa")
            
        return PersonOut(**resultado)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar pessoa: {e}")
        raise HTTPException(500, detail="Erro interno do servidor")

@app.get("/persons/{person_id}", response_model=PersonOut)
def get_person(person_id: int):
    """Buscar uma pessoa por ID"""
    try:
        resultado = get_person_db(person_id)
        
        if not resultado:
            raise HTTPException(404, detail="Pessoa não encontrada")
            
        return PersonOut(**resultado)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar pessoa {person_id}: {e}")
        raise HTTPException(500, detail="Erro interno do servidor")

@app.get("/persons", response_model=Dict[str, Any])
def list_persons(
    limit: int = Query(50, ge=1, le=100, description="Número de itens por página"),
    offset: int = Query(0, ge=0, description="Número de itens para pular")
):
    """Listar pessoas com paginação"""
    try:
        persons, total = list_persons_db(limit, offset)
        
        return {
            "persons": [PersonOut(**person) for person in persons],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": (offset + limit) < total
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar pessoas: {e}")
        raise HTTPException(500, detail="Erro interno do servidor")

@app.put("/persons/{person_id}", response_model=PersonOut)
def update_person(person_id: int, person_update: PersonUpdate):
    """Atualizar uma pessoa"""
    try:
        # Verifica se a pessoa existe
        existing_person = get_person_db(person_id)
        if not existing_person:
            raise HTTPException(404, detail="Pessoa não encontrada")
        
        # Prepara dados para atualização
        update_data = {}
        
        # Atualiza apenas os campos fornecidos
        if person_update.first_name is not None:
            update_data['first_name'] = person_update.first_name
        if person_update.last_name is not None:
            update_data['last_name'] = person_update.last_name
        if person_update.age is not None:
            update_data['age'] = person_update.age
        if person_update.height_cm is not None:
            update_data['height_cm'] = person_update.height_cm
        if person_update.weight_kg is not None:
            update_data['weight_kg'] = person_update.weight_kg
        
        # Se CEP foi fornecido, busca o endereço
        if person_update.cep is not None:
            endereco = fetch_via_cep(person_update.cep)
            if endereco:
                update_data.update({
                    'cep': endereco.get("cep"),
                    'street': endereco.get("street"),
                    'neighborhood': endereco.get("neighborhood"),
                    'city': endereco.get("city"),
                    'state': endereco.get("state")
                })
            else:
                raise HTTPException(400, detail=f"CEP {person_update.cep} não encontrado ou inválido")
        
        # Atualiza no banco
        resultado = update_person_db(person_id, update_data)
        
        if not resultado:
            raise HTTPException(500, detail="Erro ao atualizar pessoa")
            
        return PersonOut(**resultado)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar pessoa {person_id}: {e}")
        raise HTTPException(500, detail="Erro interno do servidor")

@app.delete("/persons/{person_id}")
def delete_person(person_id: int):
    """Remover uma pessoa"""
    try:
        success = delete_person_db(person_id)
        
        if not success:
            raise HTTPException(404, detail="Pessoa não encontrada")
            
        return {"message": "Pessoa removida com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover pessoa {person_id}: {e}")
        raise HTTPException(500, detail="Erro interno do servidor")

# ---------- Rota específica para atualizar apenas o CEP ----------
@app.patch("/persons/{person_id}/cep", response_model=PersonOut)
def update_person_cep(person_id: int, cep_data: CEPUpdate):
    """Atualizar apenas o CEP de uma pessoa"""
    try:
        # Verifica se a pessoa existe
        existing_person = get_person_db(person_id)
        if not existing_person:
            raise HTTPException(404, detail="Pessoa não encontrada")
        
        # Busca endereço pelo novo CEP
        endereco = fetch_via_cep(cep_data.cep)
        if not endereco:
            raise HTTPException(400, detail=f"CEP {cep_data.cep} não encontrado ou inválido")
        
        # Atualiza apenas dados de endereço
        update_data = {
            'cep': endereco.get("cep"),
            'street': endereco.get("street"),
            'neighborhood': endereco.get("neighborhood"),
            'city': endereco.get("city"),
            'state': endereco.get("state")
        }
        
        resultado = update_person_db(person_id, update_data)
        
        if not resultado:
            raise HTTPException(500, detail="Erro ao atualizar CEP")
            
        return PersonOut(**resultado)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar CEP da pessoa {person_id}: {e}")
        raise HTTPException(500, detail="Erro interno do servidor")

# ---------- Rota para consultar CEP (útil para frontend) ----------
@app.get("/cep/{cep}", response_model=AddressInfo)
def get_address_by_cep(cep: str):
    """Consultar endereço por CEP"""
    try:
        # Remove caracteres não numéricos
        cep_limpo = re.sub(r"\D", "", cep)
        if len(cep_limpo) != 8:
            raise HTTPException(400, detail="CEP deve ter 8 dígitos")
        
        endereco = fetch_via_cep(cep_limpo)
        if not endereco:
            raise HTTPException(404, detail="CEP não encontrado")
            
        return AddressInfo(**endereco)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao consultar CEP {cep}: {e}")
        raise HTTPException(500, detail="Erro interno do servidor")

# ---------- Rota para webhook (mantida para compatibilidade) ----------
@app.post("/webhook/persons", response_model=PersonOut, status_code=201)
def create_person_webhook(person: PersonIn):
    """Webhook para criar pessoa (compatibilidade com versão anterior)"""
    return create_person(person)