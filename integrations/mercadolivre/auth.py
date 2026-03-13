# auth.py
import os
import logging
import psycopg2
import requests
from dotenv import load_dotenv
from db.db import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

# --------------------- CONFIG ---------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# carrega .env
load_dotenv()

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

# --------------------- DB ---------------------
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# --------------------- AUTH LINK ---------------------
def generate_auth_link(cliente_id: int) -> str:
    """
    Gera o link de autorização do Mercado Livre.
    O state retorna no callback com o cliente_id.
    """
    return (
        "https://auth.mercadolibre.com/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={cliente_id}"
    )

# --------------------- TROCAR CODE POR TOKEN ---------------------
def exchange_code_for_token(cliente_id: int, code: str) -> dict:
    """
    Troca o code retornado pelo ML por access_token e refresh_token.
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

        response = requests.post(url, data=payload)
        response.raise_for_status()

        data = response.json()

        if "access_token" not in data:
            raise Exception(f"Erro ao obter token: {data}")

        update_tokens(
            cliente_id,
            data["access_token"],
            data["refresh_token"]
        )

        logging.info(f"Tokens atualizados para cliente {cliente_id}")

        return data

    except Exception as e:
        logging.error(f"Erro ao trocar code por token: {e}")
        raise

# --------------------- BUSCAR TOKEN ---------------------
def get_token(cliente_id: int):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT access_token, refresh_token
        FROM marketplace_accounts
        WHERE cliente_id=%s AND marketplace='Mercado Livre'
        """,
        (cliente_id,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "access_token": row[0],
        "refresh_token": row[1]
    }

# --------------------- SALVAR TOKENS ---------------------
def update_tokens(cliente_id: int, access_token: str, refresh_token: str):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO marketplace_accounts
        (cliente_id, marketplace, access_token, refresh_token)
        VALUES (%s,'Mercado Livre',%s,%s)

        ON CONFLICT (cliente_id, marketplace)
        DO UPDATE SET
        access_token = EXCLUDED.access_token,
        refresh_token = EXCLUDED.refresh_token
        """,
        (cliente_id, access_token, refresh_token)
    )

    conn.commit()

    cur.close()
    conn.close()

# --------------------- REFRESH TOKEN ---------------------
def refresh_ml_token(cliente_id: int):

    tokens = get_token(cliente_id)

    if not tokens:
        raise Exception("Cliente não possui refresh_token")

    refresh_token = tokens["refresh_token"]

    url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token
    }

    response = requests.post(url, data=payload)

    response.raise_for_status()

    data = response.json()

    if "access_token" not in data:
        raise Exception(f"Erro ao atualizar token: {data}")

    update_tokens(
        cliente_id,
        data["access_token"],
        data["refresh_token"]
    )

    logging.info(f"Token atualizado automaticamente para cliente {cliente_id}")

    return data