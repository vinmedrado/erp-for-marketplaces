# suppliers/wedrop.py
import os
import psycopg2
import logging
import requests
from db.db import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def get_db_connection():
    """Retorna uma conexão com o banco de dados."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def wedrop_catalog(cliente_id: int):
    """
    Faz login no Wedrop, baixa o catálogo e salva como Excel.
    """
    try:
        # Busca credenciais do cliente no banco
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT email, password FROM suppliers WHERE cliente_id = %s AND supplier_name = 'Wedrop'",
            (cliente_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            logging.error(f"Credenciais Wedrop não encontradas para cliente {cliente_id}")
            raise Exception(f"Credenciais Wedrop não encontradas para cliente {cliente_id}")

        email, password = row
        logging.info(f"🔐 Fazendo login Wedrop para cliente {cliente_id}...")

        # Login Wedrop
        login_resp = requests.post(
            "https://api.wedrop.com.br/v3/api/auth",
            json={"email": email, "password": password}
        )
        login_resp.raise_for_status()
        token = login_resp.json().get("access_token")
        if not token:
            logging.error("Falha no login Wedrop: token não retornado")
            raise Exception("Falha no login Wedrop")

        headers = {"Authorization": f"Bearer {token}"}

        # Download do catálogo
        logging.info("⬇️ Baixando catálogo...")
        url = "https://api.wedrop.com.br/v3/api/catalog/export/excel"
        catalog_resp = requests.get(url, headers=headers)
        catalog_resp.raise_for_status()

        os.makedirs("downloads", exist_ok=True)
        file_path = f"downloads/catalogo_{cliente_id}.xlsx"
        with open(file_path, "wb") as f:
            f.write(catalog_resp.content)

        logging.info(f"✅ Catálogo Wedrop baixado para cliente {cliente_id} em '{file_path}'")

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição Wedrop: {e}")
        raise
    except psycopg2.Error as e:
        logging.error(f"Erro no banco de dados: {e}")
        raise
    except Exception as e:
        logging.error(f"Erro geral ao processar catálogo Wedrop: {e}")
        raise