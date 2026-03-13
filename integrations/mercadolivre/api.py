# api.py
import os
import requests
import logging
from .auth import get_token, exchange_code_for_token, CLIENT_ID, CLIENT_SECRET

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

BASE_URL = "https://api.mercadolibre.com"

def get_headers(cliente_id: int) -> dict:
    """Retorna headers de autorização para o cliente."""
    tokens = get_token(cliente_id)
    if not tokens:
        logging.error(f"Cliente {cliente_id} não autorizado")
        raise Exception("Cliente não autorizado")
    return {"Authorization": f"Bearer {tokens['access_token']}"}

def refresh_token(cliente_id: int) -> dict:
    """
    Faz refresh do token do cliente.
    Atualiza o banco com os novos tokens.
    """
    tokens = get_token(cliente_id)
    if not tokens or "refresh_token" not in tokens:
        logging.error(f"Cliente {cliente_id} não possui refresh_token")
        raise Exception("Não há refresh_token disponível")

    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"]
    }

    try:
        r = requests.post(f"{BASE_URL}/oauth/token", data=payload)
        r.raise_for_status()
        data = r.json()

        # Atualiza o banco diretamente
        # ML retorna access_token e refresh_token no refresh
        conn_tokens = {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token")
        }
        if not conn_tokens["access_token"] or not conn_tokens["refresh_token"]:
            raise Exception(f"Falha ao obter tokens de refresh: {data}")

        # Atualiza banco usando auth.py (função genérica para inserir/update tokens)
        # Precisamos de uma função separada para update de tokens
        from .auth import update_tokens
        update_tokens(cliente_id, conn_tokens["access_token"], conn_tokens["refresh_token"])

        logging.info(f"Tokens do cliente {cliente_id} atualizados via refresh")
        return data

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição de refresh_token ML: {e}")
        raise
    except Exception as e:
        logging.error(f"Erro ao atualizar tokens via refresh: {e}")
        raise

def get_user_info(cliente_id: int) -> dict:
    """Retorna informações do usuário do ML."""
    headers = get_headers(cliente_id)
    r = requests.get(f"{BASE_URL}/users/me", headers=headers)

    if r.status_code == 401:
        logging.info(f"Access_token expirado para cliente {cliente_id}, tentando refresh...")
        refresh_token(cliente_id)
        headers = get_headers(cliente_id)
        r = requests.get(f"{BASE_URL}/users/me", headers=headers)

    r.raise_for_status()
    return r.json()

def get_items(cliente_id: int) -> dict:
    """Retorna itens do usuário ML."""
    user_info = get_user_info(cliente_id)
    user_id = user_info.get("id")
    headers = get_headers(cliente_id)
    r = requests.get(f"{BASE_URL}/users/{user_id}/items/search", headers=headers)
    r.raise_for_status()
    return r.json()