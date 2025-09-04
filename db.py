import os
import psycopg2
from psycopg2 import DatabaseError
from dotenv import load_dotenv
from contextlib import contextmanager
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv(override=True)

DB_URL = os.getenv("SUPABASE_DB_URL")
if not DB_URL:
    raise RuntimeError("SUPABASE_DB_URL não definida!")

def get_connection():
    """Cria uma nova conexão com o banco de dados"""
    try:
        return psycopg2.connect(DB_URL)
    except DatabaseError as e:
        logger.error(f"Erro ao conectar com o banco: {e}")
        raise

@contextmanager
def get_db_connection():
    """Context manager para gerenciar conexões automaticamente"""
    conn = None
    try:
        conn = get_connection()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Erro na operação do banco: {e}")
        raise
    finally:
        if conn:
            conn.close()

def ensure_schema():
    """Cria tabela se não existir"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.persons (
                        id BIGSERIAL PRIMARY KEY,
                        first_name TEXT NOT NULL CHECK (LENGTH(first_name) > 0 AND LENGTH(first_name) <= 80),
                        last_name  TEXT NOT NULL CHECK (LENGTH(last_name) > 0 AND LENGTH(last_name) <= 80),
                        age        INT  NOT NULL CHECK (age >= 0 AND age <= 120),
                        height_cm  NUMERIC(5,2) CHECK (height_cm IS NULL OR (height_cm >= 0 AND height_cm <= 300)),
                        weight_kg  NUMERIC(5,2) CHECK (weight_kg IS NULL OR (weight_kg >= 0 AND weight_kg <= 500)),
                        cep        TEXT CHECK (cep IS NULL OR LENGTH(cep) = 8),
                        street     TEXT,
                        neighborhood TEXT,
                        city       TEXT,
                        state      TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """)
                
                # Cria índices para melhor performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_persons_cep ON public.persons(cep);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_persons_created_at ON public.persons(created_at);
                """)
                
                # Função para atualizar updated_at automaticamente
                cur.execute("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = NOW();
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                """)
                
                # Trigger para atualizar updated_at
                cur.execute("""
                    DROP TRIGGER IF EXISTS update_persons_updated_at ON public.persons;
                    CREATE TRIGGER update_persons_updated_at
                        BEFORE UPDATE ON public.persons
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """)
                
        logger.info("✅ Schema do banco criado/atualizado com sucesso")
        
    except Exception as e:
        logger.error(f"⚠️ Erro na criação do schema: {e}")
        raise

def init_pool():
    """Inicializa o 'pool' (função de compatibilidade)"""
    ensure_schema()
    logger.info("✅ Banco inicializado")

def close_pool():
    """Fecha o 'pool' (função de compatibilidade)"""
    logger.info("✅ Conexões fechadas")

# Funções CRUD para Person
def create_person_db(person_data: dict) -> dict:
    """Cria uma nova pessoa no banco"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO persons 
                (first_name, last_name, age, height_cm, weight_kg, cep, street, neighborhood, city, state)
                VALUES (%(first_name)s, %(last_name)s, %(age)s, %(height_cm)s, %(weight_kg)s, 
                        %(cep)s, %(street)s, %(neighborhood)s, %(city)s, %(state)s)
                RETURNING id, first_name, last_name, age, height_cm, weight_kg, cep, 
                         street, neighborhood, city, state, created_at;
            """, person_data)
            
            result = cur.fetchone()
            if result:
                return {
                    'id': result[0],
                    'first_name': result[1],
                    'last_name': result[2],
                    'age': result[3],
                    'height_cm': result[4],
                    'weight_kg': result[5],
                    'cep': result[6],
                    'street': result[7],
                    'neighborhood': result[8],
                    'city': result[9],
                    'state': result[10],
                    'created_at': result[11]
                }
            return None

def get_person_db(person_id: int) -> dict:
    """Busca uma pessoa por ID"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, first_name, last_name, age, height_cm, weight_kg, cep, 
                       street, neighborhood, city, state, created_at
                FROM persons WHERE id = %s;
            """, (person_id,))
            
            result = cur.fetchone()
            if result:
                return {
                    'id': result[0],
                    'first_name': result[1],
                    'last_name': result[2],
                    'age': result[3],
                    'height_cm': result[4],
                    'weight_kg': result[5],
                    'cep': result[6],
                    'street': result[7],
                    'neighborhood': result[8],
                    'city': result[9],
                    'state': result[10],
                    'created_at': result[11]
                }
            return None

def update_person_db(person_id: int, person_data: dict) -> dict:
    """Atualiza uma pessoa"""
    # Constrói a query dinamicamente apenas com os campos fornecidos
    fields = []
    values = []
    
    for key, value in person_data.items():
        if value is not None:
            fields.append(f"{key} = %s")
            values.append(value)
    
    if not fields:
        return get_person_db(person_id)
    
    values.append(person_id)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE persons SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id, first_name, last_name, age, height_cm, weight_kg, cep, 
                         street, neighborhood, city, state, created_at;
            """, values)
            
            result = cur.fetchone()
            if result:
                return {
                    'id': result[0],
                    'first_name': result[1],
                    'last_name': result[2],
                    'age': result[3],
                    'height_cm': result[4],
                    'weight_kg': result[5],
                    'cep': result[6],
                    'street': result[7],
                    'neighborhood': result[8],
                    'city': result[9],
                    'state': result[10],
                    'created_at': result[11]
                }
            return None

def delete_person_db(person_id: int) -> bool:
    """Remove uma pessoa"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM persons WHERE id = %s;", (person_id,))
            return cur.rowcount > 0

def list_persons_db(limit: int = 50, offset: int = 0) -> tuple:
    """Lista pessoas com paginação"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Conta total de registros
            cur.execute("SELECT COUNT(*) FROM persons;")
            total = cur.fetchone()[0]
            
            # Busca os registros paginados
            cur.execute("""
                SELECT id, first_name, last_name, age, height_cm, weight_kg, cep, 
                       street, neighborhood, city, state, created_at
                FROM persons 
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
            """, (limit, offset))
            
            results = cur.fetchall()
            persons = []
            
            for result in results:
                persons.append({
                    'id': result[0],
                    'first_name': result[1],
                    'last_name': result[2],
                    'age': result[3],
                    'height_cm': result[4],
                    'weight_kg': result[5],
                    'cep': result[6],
                    'street': result[7],
                    'neighborhood': result[8],
                    'city': result[9],
                    'state': result[10],
                    'created_at': result[11]
                })
            
            return persons, total