import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)

DB_URL = os.getenv("SUPABASE_DB_URL")
if not DB_URL:
    raise RuntimeError("SUPABASE_DB_URL não definida!")

# Conexão SIMPLES - sem pool complexo
def get_connection():
    return psycopg2.connect(DB_URL)

def ensure_schema():
    """Cria tabela se não existir - versão simples"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.persons (
                    id BIGSERIAL PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name  TEXT NOT NULL,
                    age        INT  NOT NULL,
                    height_cm  NUMERIC(5,2),
                    weight_kg  NUMERIC(5,2),
                    cep        TEXT,
                    street     TEXT,
                    neighborhood TEXT,
                    city       TEXT,
                    state      TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            conn.commit()
    except Exception as e:
        print(f"⚠️  Aviso na criação do schema: {e}")
    finally:
        conn.close()

# Funções vazias para compatibilidade
def init_pool():
    print("✅ Banco inicializado (sem pool)")

def close_pool():
    print("✅ Conexões fechadas")