import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)
DB_URL = os.getenv("SUPABASE_DB_URL")

print("🔍 Testando conexão com Supabase...")
print(f"URL do DB: {DB_URL}")

try:
    # Tenta uma conexão direta e uma query simples
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    print("✅ Conectado ao Supabase!")

    cur.execute("SELECT NOW();")
    result = cur.fetchone()
    print(f"✅ Query executada. Hora do servidor: {result[0]}")

    cur.close()
    conn.close()
    print("✅ Conexão fechada.")

except Exception as e:
    print(f"❌ ERRO: {e}")
    print("👆 Este é o provável culpado do 504!")