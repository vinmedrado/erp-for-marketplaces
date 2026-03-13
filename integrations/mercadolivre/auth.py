# auth.py
import os
import psycopg2
import logging
from db.db import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from dotenv import load_dotenv
import requests

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Carrega variáveis de ambiente
load_dotenv()

# Mercado Livre
CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("ML_REDIRECT_URI")

def get_db_connection():
    """Retorna uma conexão com o banco de dados."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def generate_auth_link(cliente_id: int) -> str:
    """Gera o link de autorização do Mercado Livre para o cliente."""
    return f"https://auth.mercadolibre.com/authorization?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"

def exchange_code_for_token(cliente_id: int, code: str) -> dict:
    """
    Troca o code retornado pelo ML por access_token e refresh_token.
    Atualiza o banco com os tokens.
    """
    try:
        url = "https://api.mercadolibre.com/oauth/token"
        payload = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI
        }

        r = requests.post(url, data=payload)
        r.raise_for_status()
        data = r.json()

        if "access_token" not in data or "refresh_token" not in data:
            raise Exception(f"Falha ao obter tokens: {data}")

        # Atualiza o banco de dados
        update_tokens(cliente_id, data["access_token"], data["refresh_token"])

        logging.info(f"Tokens atualizados para cliente {cliente_id}")
        return data

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição ML: {e}")
        raise
    except Exception as e:
        logging.error(f"Erro ao atualizar tokens: {e}")
        raise

def get_token(cliente_id: int) -> dict:
    """
    Retorna os tokens do cliente.
    Retorna None se não houver token.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT access_token, refresh_token FROM marketplace_accounts WHERE cliente_id=%s AND marketplace='Mercado Livre'",
            (cliente_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            logging.warning(f"Cliente {cliente_id} não possui tokens")
            return None
        return {"access_token": row[0], "refresh_token": row[1]}
    except Exception as e:
        logging.error(f"Erro ao buscar tokens para cliente {cliente_id}: {e}")
        raise

def update_tokens(cliente_id: int, access_token: str, refresh_token: str):
    """
    Atualiza os tokens no banco de dados para um cliente.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO marketplace_accounts (cliente_id, marketplace, access_token, refresh_token)
            VALUES (%s, 'Mercado Livre', %s, %s)
            ON CONFLICT (cliente_id, marketplace)
            DO UPDATE SET access_token=EXCLUDED.access_token, refresh_token=EXCLUDED.refresh_token
        """, (cliente_id, access_token, refresh_token))
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Tokens gravados/atualizados para cliente {cliente_id}")
    except Exception as e:
        logging.error(f"Erro ao atualizar tokens no banco para cliente {cliente_id}: {e}")
        raise

def refresh_ml_token(cliente_id: int):
    """
    Usa o refresh_token do cliente para gerar um novo access_token e salvar no DB.
    Retorna os novos tokens.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT refresh_token FROM ml_tokens WHERE cliente_id = %s", (cliente_id,))
    row = cur.fetchone()
    if not row:
        raise Exception("Refresh token não encontrado para esse cliente")
    refresh_token = row[0]

    # Requisição ao ML para gerar novo access_token
    response = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token
        }
    )
    data = response.json()
    if "access_token" not in data:
        raise Exception(f"Falha ao atualizar token: {data}")

    # Atualiza no banco
    cur.execute("""
        UPDATE ml_tokens
        SET access_token = %s, refresh_token = %s, expires_in = %s
        WHERE cliente_id = %s
    """, (data["access_token"], data["refresh_token"], data["expires_in"], cliente_id))
    conn.commit()
    cur.close()
    conn.close()
    return data