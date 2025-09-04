import re
import requests
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from models import PersonIn, PersonOut
from db import init_pool, close_pool, ensure_schema, get_connection

app = FastAPI(title="Mini API (FastAPI + Supabase + ViaCEP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    ensure_schema()  # Cria tabelas se precisar
    print("✅ API iniciada com sucesso!")

@app.on_event("shutdown")
def shutdown():
    print("✅ API encerrada")

@app.get("/health")
def health():
    return {"status": "ok", "message": "API funcionando!"}

# ---------- Helper ViaCEP SIMPLES ----------
def fetch_via_cep(cep: str) -> Optional[Dict[str, Any]]:
    try:
        cep_limpo = re.sub(r"\D", "", cep)
        if len(cep_limpo) != 8:
            return None
            
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("erro"):
                return {
                    "cep": data.get("cep"),
                    "street": data.get("logradouro"),
                    "neighborhood": data.get("bairro"),
                    "city": data.get("localidade"),
                    "state": data.get("uf")
                }
        return None
    except:
        return None

# ---------- Rota Principal SIMPLES ----------
@app.post("/webhook/persons", response_model=PersonOut, status_code=201)
def create_person(person: PersonIn):
    try:
        # Busca endereço pelo CEP
        endereco = fetch_via_cep(person.cep) if person.cep else None
        
        # Conexão SIMPLES com o banco
        conn = get_connection()
        with conn.cursor() as cur:
            # Insere pessoa
            cur.execute("""
                INSERT INTO persons 
                (first_name, last_name, age, height_cm, weight_kg, cep, street, neighborhood, city, state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                person.first_name, person.last_name, person.age,
                person.height_cm, person.weight_kg,
                endereco.get("cep") if endereco else person.cep,
                endereco.get("street") if endereco else None,
                endereco.get("neighborhood") if endereco else None,
                endereco.get("city") if endereco else None,
                endereco.get("state") if endereco else None
            ))
            
            novo_id = cur.fetchone()[0]
            conn.commit()
            
            # Retorna os dados inseridos
            return PersonOut(
                id=novo_id,
                first_name=person.first_name,
                last_name=person.last_name,
                age=person.age,
                height_cm=person.height_cm,
                weight_kg=person.weight_kg,
                cep=person.cep
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
    finally:
        if conn:
            conn.close()

# ---------- Rota para atualizar CEP ----------
@app.post("/persons/{person_id}/cep", response_model=PersonOut)
def update_cep(person_id: int, cep_data: Dict[str, str] = Body(...)):
    cep = cep_data.get("cep")
    if not cep:
        raise HTTPException(400, detail="CEP é obrigatório")
        
    endereco = fetch_via_cep(cep)
    if not endereco:
        raise HTTPException(400, detail="CEP inválido")
    
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE persons 
                SET cep=%s, street=%s, neighborhood=%s, city=%s, state=%s
                WHERE id=%s
                RETURNING id, first_name, last_name, age, height_cm, weight_kg, cep;
            """, (
                endereco["cep"], endereco["street"], endereco["neighborhood"],
                endereco["city"], endereco["state"], person_id
            ))
            
            resultado = cur.fetchone()
            conn.commit()
            
            if not resultado:
                raise HTTPException(404, detail="Pessoa não encontrada")
                
            return PersonOut(
                id=resultado[0],
                first_name=resultado[1],
                last_name=resultado[2],
                age=resultado[3],
                height_cm=resultado[4],
                weight_kg=resultado[5],
                cep=resultado[6]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
    finally:
        if conn:
            conn.close()